# OpenClaw Client Harness

用于本地 OpenClaw gateway 负载测试的 Python harness。

当前第一版主要面向本地 `WSL2 + Docker` 工作流：

- 需要时从当前仓库构建本地 OpenClaw 镜像
- 在独立的 localhost 端口上启动隔离的 gateway 容器
- 通过 gateway WebSocket API 驱动 `chat.send -> agent.wait -> chat.history`
- 将每次运行产物写入 `out/<timestamp>_<scenario>/`
- 采集 `latency.csv`、`summary.json`、`meta.json`、`docker_stats.csv`
- 在负载开始前写出 `preflight.json`，记录目标 URL、healthcheck、发现到的 PID，以及 collector 附着计划
- 将 `docker stats`、`pidstat`、`iostat`、`perf stat` 和 `perf record` 接成可选 collector
- 把 `docker stats`、`pidstat`、`iostat` 和 `perf stat` 的原始输出解析成结构化 CSV/JSON 报告
- 写出 `environment.json`，记录当前宿主机实际具备哪些观测能力
- 支持从 `tasks/*.md` 读取真实任务式 prompt，模拟更接近实际使用的交互延迟

默认场景使用 `/context list`，因此不依赖模型 key。
本地 Docker 场景遵循当前推荐的 WSL 策略：优先使用 `docker stats` + `pidstat`，
`perf` 默认关闭，等迁移到 Linux VPS 后再作为正式采集手段启用。
`docker_single_100_summary.json` 和 `docker_multi_100_summary.json` 现在也会开启
`docker_stats`、`pidstat` 和 `iostat`，因此即使是最基础的 `/context list`
大样本对比，也会在 `summary.json` 里保留容器 CPU/内存、进程 CPU/内存/IO 和磁盘指标汇总。

## Latency Phases

`summary.json` 和 `latency.csv` 里的 phase 由 harness 客户端在
`src/openclaw_harness/runner.py` 中划分，不是 OpenClaw gateway 原生输出的 phase。

- `connect`
  - `GatewayClient.connect()` 的耗时。
  - 表示 benchmark 客户端与 gateway 建立 WebSocket 连接并完成 `connect` 握手的时间。
  - 这是按 worker 记录的建连成本，不是每条请求都重新计算一次。
- `send`
  - `chat.send` 的耗时。
  - 表示客户端把命令或任务提交给 gateway 的时间。
- `wait`
  - `agent.wait` 的耗时。
  - 表示请求已经提交后，等待 agent 执行并返回完成状态的时间。
  - 这个阶段通常最接近“真实任务处理时间”，也是最容易成为主要瓶颈的阶段。
- `history`
  - `chat.history` 的耗时。
  - 表示在任务完成后，再向 gateway 读取该 `sessionKey` 对应消息历史的时间。
  - 这里是从 OpenClaw gateway 的 session history 中读回到 benchmark Python 客户端，不是再次请求模型。
- `total`
  - 从 `send` 开始到 `history` 结束的总耗时。
  - 当前口径下 `total` 不包含 `connect`。

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
python -m openclaw_harness run --scenario scenarios/docker_single_100_summary.json
python -m openclaw_harness run --scenario scenarios/docker_multi_100_summary.json
python -m openclaw_harness run --scenario scenarios/docker_single_resource_profile.json
python -m openclaw_harness run --scenario scenarios/docker_multi_resource_profile.json
python -m openclaw_harness run --scenario scenarios/docker_single_task_context.json
python -m openclaw_harness run --scenario scenarios/docker_single_task_comprehension.json
python -m openclaw_harness run --scenario scenarios/docker_multi_task_mix.json
python -m openclaw_harness run --scenario scenarios/docker_single_task_semianalysis_100_summary.json
python -m openclaw_harness run --scenario scenarios/docker_multi_task_semianalysis_100_summary.json
python -m openclaw_harness run --scenario scenarios/docker_single_task_semianalysis_smoke.json
python -m openclaw_harness run --scenario scenarios/docker_multi_task_semianalysis_smoke.json
```

上面这些命令都是同一个入口：`python -m openclaw_harness run --scenario <file>`。
harness 只直接接收 scenario JSON；是否使用 `tasks/*.md`，由 scenario 里的 `client`
配置决定。

使用 `.deps` 回退方案：

```bash
cd ~/openclaw/benchmarks/client-harness
export PYTHONPATH="$PWD/.deps:$PWD/src"
python3 -m openclaw_harness run --scenario scenarios/docker_single.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_multi.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_single_100_summary.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_multi_100_summary.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_single_resource_profile.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_multi_resource_profile.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_single_task_context.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_multi_task_mix.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_single_task_semianalysis_100_summary.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_multi_task_semianalysis_100_summary.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_single_task_semianalysis_smoke.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_multi_task_semianalysis_smoke.json --output-root out
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
- 大样本 summary-only 场景：例如 `docker_single_100_summary.json`、`docker_multi_100_summary.json`，用于快速对比 100 次请求下的单 worker / 多 worker 汇总结果
- 资源画像场景：例如 `docker_single_resource_profile.json`、`docker_multi_resource_profile.json`，用于一起观察 latency、容器 CPU/内存、进程 CPU/内存/IO、以及磁盘 await/%util/队列长度
- 任务驱动场景：例如 `docker_single_task_context.json`、`docker_single_task_comprehension.json`、`docker_multi_task_mix.json`、`docker_single_task_semianalysis_smoke.json`、`docker_multi_task_semianalysis_smoke.json`、`docker_single_task_semianalysis_100_summary.json`、`docker_multi_task_semianalysis_100_summary.json`，从 `tasks/*.md` 加载 prompt 来模拟更真实的使用

当 `client.task_file` 存在时，harness 会优先使用任务文件中的 `prompt`；
`client.message` 仍会保留在场景里，但只作为回退值。

## Scenario 和 Task 的关系

可以把 `scenarios/*.json` 理解成“运行计划”，把 `tasks/*.md` 理解成“提示词模板”。

- 直接 message 场景：在 scenario 里设置 `client.message`
- task 驱动场景：在 scenario 里设置 `client.task_file`

最简单的 `/context list` 大样本场景长这样：

```json
{
  "name": "docker-single-100-summary",
  "client": {
    "message": "/context list"
  }
}
```

对应运行命令：

```bash
python -m openclaw_harness run --scenario scenarios/docker_single_100_summary.json
python -m openclaw_harness run --scenario scenarios/docker_multi_100_summary.json
```

task 驱动场景会在 scenario 里引用 `tasks/*.md`：

```json
{
  "name": "docker-single-task-semianalysis-100-summary",
  "client": {
    "message": "/context list",
    "task_file": "../tasks/task_05_semianalysis_title.md"
  }
}
```

对应运行命令：

```bash
python -m openclaw_harness run --scenario scenarios/docker_single_task_semianalysis_100_summary.json
python -m openclaw_harness run --scenario scenarios/docker_multi_task_semianalysis_100_summary.json
```

代码路径上，它们的区别是：

- CLI 入口在 `src/openclaw_harness/cli.py`
- scenario 加载和 task 解析在 `src/openclaw_harness/scenario.py` 和 `src/openclaw_harness/task.py`
- 如果 `client.task_file` 非空，`load_scenario()` 会读取 task frontmatter，并把 `prompt`
  写入 `scenario.client.resolved_prompt`
- 真正发给 gateway 的内容统一来自 `scenario.client.effective_message()`，也就是
  “优先用 task prompt，否则退回到 `client.message`”
- 实际压测执行链在 `src/openclaw_harness/runner.py`，每次请求都会走
  `chat.send -> agent.wait -> chat.history`

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
- 解析后的 collector 产物会和原始文件一起写在同一目录下，例如 `docker_stats.summary.json`、`pidstat_cpu.csv`、`pidstat.summary.json`、`iostat.summary.json`、`perf_stat.summary.json`。

## 执行测试

写完 `task` 和 `scenario` 之后，真正执行测试的入口只有一个：`run` 子命令。

```bash
cd client-harness
python -m openclaw_harness run --scenario scenarios/<your_scenario>.json
```

如果已经安装了包脚本，也可以直接用：

```bash
openclaw-harness run --scenario scenarios/<your_scenario>.json
```

执行时建议记住下面这几个规则：

- `scenario` 是运行计划，必须传给 CLI。
- `client.task_file` 非空时，harness 会先读取对应的 `tasks/*.md`，再把 task 里的 `prompt` 作为实际发送内容。
- `client.message` 只是在没有 `task_file` 时才会直接发送，或者作为可读的默认值保留在 scenario 里。
- 运行产物默认会写到 `out/<timestamp>_<scenario>/`，里面会有 `scenario.resolved.json`、`preflight.json`、`meta.json`、`summary.json`、`latency.csv` 等文件。

最常见的三种用法是：

- 纯 message 场景：只写 `client.message`，不写 `client.task_file`。
- 复用现有 task：在新的 scenario 里把 `client.task_file` 指向已有的 `tasks/*.md`。
- 新建 task：先复制 `tasks/TASK_TEMPLATE.md`，再在 scenario 里引用它。

对应的代码位置也很集中：

- `client-harness/src/openclaw_harness/cli.py`：解析 `run --scenario ...` 命令。
- `client-harness/src/openclaw_harness/scenario.py`：加载 scenario，解析 `task_file`，生成最终的 `resolved_prompt`。
- `client-harness/src/openclaw_harness/runner.py`：真正执行 `chat.send -> agent.wait -> chat.history`，并写出运行产物。

如果你想快速检查某个场景到底会发什么，可以先看 `scenario.resolved.json` 里的 `client.resolved_prompt`，它就是最终发送给 gateway 的内容。
