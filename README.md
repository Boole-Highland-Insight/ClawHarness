# OpenClaw Client Harness

用于本地 OpenClaw gateway 负载测试的 Python harness。

当前第一版主要面向本地 `WSL2 + Docker` 工作流：

- 需要时从当前仓库构建本地 OpenClaw 镜像
- 在独立的 localhost 端口上启动隔离的 gateway 容器
- 通过 gateway WebSocket API 驱动 `chat.send -> agent.wait -> chat.history`
- 将每次运行产物写入 `out/<timestamp>_<scenario>/`
- 采集 `latency.csv`、`summary.json`、`meta.json`、`docker_stats.csv`
- 在负载开始前写出 `preflight.json`，记录目标 URL、healthcheck、发现到的 PID，以及 collector 附着计划
- 将 `pidstat`、`perf stat` 和 `perf record` 接成可选 collector
- 把 `pidstat` 和 `perf stat` 的原始输出解析成结构化 CSV/JSON 报告
- 写出 `environment.json`，记录当前宿主机实际具备哪些观测能力
- 支持从 `tasks/*.md` 读取真实任务式 prompt，模拟更接近实际使用的交互延迟

默认场景使用 `/context list`，因此不依赖模型 key。
本地 Docker 场景遵循当前推荐的 WSL 策略：优先使用 `docker stats` + `pidstat`，
`perf` 默认关闭，等迁移到 Linux VPS 后再作为正式采集手段启用。

## 环境准备

推荐方式：

```bash
cd ~/openclaw/benchmarks/client-harness
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

如果没有安装 `python3-venv`，可以使用下面的回退方案：

```bash
cd ~/openclaw/benchmarks/client-harness
python3 -m pip install --break-system-packages --target .deps "websockets>=14,<16"
export PYTHONPATH="$PWD/.deps:$PWD/src"
```

## 运行

使用 virtualenv：

```bash
source .venv/bin/activate
python -m openclaw_harness run --scenario scenarios/docker_single.json
python -m openclaw_harness run --scenario scenarios/docker_multi.json
python -m openclaw_harness run --scenario scenarios/docker_single_task_context.json
python -m openclaw_harness run --scenario scenarios/docker_single_task_comprehension.json
python -m openclaw_harness run --scenario scenarios/docker_multi_task_mix.json
```

使用 `.deps` 回退方案：

```bash
cd ~/openclaw/benchmarks/client-harness
export PYTHONPATH="$PWD/.deps:$PWD/src"
python3 -m openclaw_harness run --scenario scenarios/docker_single.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_multi.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_single_task_context.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_multi_task_mix.json --output-root out
```

VPS 场景模板：

```bash
python3 -m openclaw_harness run --scenario scenarios/vps_host_direct_single.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/vps_docker_single.json --output-root out
```

辅助脚本：

```bash
bash scripts/install_ubuntu_tools.sh
bash scripts/run_local_wsl.sh
bash scripts/run_vps_host_direct.sh scenarios/vps_host_direct_single.json
bash scripts/run_vps_docker.sh scenarios/vps_docker_single.json
```

## 任务文件

任务文件位于 `tasks/` 目录，格式参考 `pinchbench` 风格的 `Markdown + frontmatter`。
首版只把任务文件作为 prompt 来源，不包含 workspace 输入文件和自动评分。

一个最小任务文件示例如下：

```md
---
id: task_example
name: Example Task
category: example
description: 示例任务
prompt: |
  请根据任务要求给出自然语言回答。
---

# Example Task

这里可以写人类可读的任务说明。
```

目前内置任务包括：

- `task_00_context_inventory.md`
- `task_01_openclaw_comprehension.md`
- `task_02_skill_discovery.md`
- `task_03_local_summary.md`
- `task_04_workflow_planning.md`

如果你想新增一个任务：

1. 复制 `tasks/TASK_TEMPLATE.md`
2. 填好 frontmatter 中的 `id`、`name`、`category`、`prompt`
3. 在 `scenarios/` 中新增或修改一个场景，让 `client.task_file` 指向该任务文件

## 场景类型

- 基础链路场景：例如 `docker_single.json`、`docker_multi.json`，继续使用 `/context list` 作为最小基准
- 任务驱动场景：例如 `docker_single_task_context.json`、`docker_single_task_comprehension.json`、`docker_multi_task_mix.json`，从 `tasks/*.md` 加载 prompt 来模拟更真实的使用

当 `client.task_file` 存在时，harness 会优先使用任务文件中的 `prompt`；
`client.message` 仍会保留在场景里，但只作为回退值。

## 说明

- 这个 harness 自己管理 Docker 容器，不使用 `~/.openclaw`。
- 容器运行时状态会保存在每次运行目录下的 `out/` 子目录里。
- 客户端 device identity 保存在 `.state/device.json`。
- `environment.json` 用来记录操作系统、内核、工具可用性，以及推荐启用的 collector 组合。
- `preflight.json` 会在负载开始前记录 runtime URL、healthcheck URL、自动发现到的 `host_pid`、`host_pid_source`，以及各个 collector 的附着目标。
- `scenario.resolved.json` 会写出最终使用的 `task_file`、`task_id`、`task_name` 和 `resolved_prompt`。
- `meta.json`、`summary.json`、`latency.csv` 会附带任务元数据，方便后续归档和对比。
- `host_direct` 场景默认假设 harness 和 gateway 跑在同一台 VPS 上。
- `host_direct` 会尝试根据配置的监听端口自动发现 `host_pid`。
- 只有在你想覆盖自动发现结果时，才需要手动填写 `runtime.host_pid`。
- 如果没有安装 `pidstat` 或 `perf`，harness 会把对应 collector 标记为 `skipped`，但整次运行仍会继续完成。
- 在 WSL 上，即使存在 `/usr/bin/perf`，如果缺少与当前内核匹配的 perf 二进制，它仍然可能不可用；这一点会在 `environment.json` 中明确标记。
- 解析后的 collector 产物会和原始文件一起写在同一目录下，例如 `pidstat_cpu.csv`、`pidstat.summary.json`、`perf_stat.summary.json`。
