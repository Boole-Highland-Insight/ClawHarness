# OpenClaw / Hermes Profiling Experiment Plan

本文档规划在当前 `client-harness` 压测能力基础上，继续扩展三类 profiling 实验：

1. 同 request 数、同发压形状下，对比不同部署拓扑的性能和时延 profile。
2. 使用短期上下文、长期记忆等记忆机制，对比 OpenClaw 与 Hermes 在多并发下的负载特征。
3. 在多 agent / tool-calling 复杂任务中，对比不同 agent 和不同拓扑机制下的系统负载、时延与可靠性。

当前仓库的 baseline 是通过 WebSocket gateway 执行 `chat.send -> agent.wait -> chat.history`，scenario 控制发压、session 和 runtime；`tasks/*.md` 当前只作为 prompt 来源。后续要做真正的多 agent / memory / tool-calling benchmark，需要在此基础上增加 task dataset adapter、memory setup/teardown、multi-agent runner 和评分逻辑。

## 0. 现有能力与缺口

### 已有能力

- `runtime.instance_num`：多容器 / 多 runtime 实例。
- `runtime.openclaw_num_per_instance`：单容器内多个 OpenClaw gateway 实例。
- `load.dispatch_mode = burst`：同一时刻释放固定数量请求。
- `load.total_requests` / `load.max_in_flight` / `load.connect_concurrency`：控制总请求数、最大在途请求数、建连并发。
- `client.session_mode` / `client.session_pool_size`：控制共享 session、按 worker/session 池复用、按请求独立 session。
- collectors：`docker_stats`、`pidstat`、`node_trace`、`iostat`、`vmstat`、可选 `perf_stat`、`perf_record`、`strace`、`npu_smi`。

### 当前缺口

- 任务层面仍是单 prompt，不能自动表达多 agent 拓扑、agent 间消息传递、私有上下文隔离。
- 没有标准 memory seed / query / cleanup 流程，无法稳定比较短期上下文和长期记忆。
- 没有 Hermes transport / Hermes scenario adapter，无法与 OpenClaw 在同一 workload schema 下公平对比。
- 没有 tool-calling trace 的统一字段，例如 tool call 数、tool latency、tool error、retrieval latency、memory read/write latency。
- 没有自动评分器，只能看 latency 和 success；对多 agent 可靠性还需要任务级 metric。

## 1. 核心实验原则

- 固定 request 数：每组主实验使用同一个 `total_requests`，先从 `100` 开始，稳定后扩到 `300`、`500`。
- 固定模型和采样参数：同一批对比中固定 vLLM endpoint、模型、`temperature=0`、`maxTokens`。
- 固定发压形状：优先使用 `dispatch_mode=burst`，`max_in_flight=total_requests`，用于观察瞬时峰值承载。
- 固定任务集：拓扑对比、memory 对比、tool-calling 对比分别使用固定任务集，不混用。
- 每组至少 3 次重复：保留 run-level 方差，不只看单次 p95/p99。
- 输出统一：所有结果落到 `res/<experiment_id>/...`，每组都保留 `scenario.resolved.json`、`summary.json`、`latency.csv`、collector summary 和对比报告。

## 2. 实验 A：相同 request 数下的部署拓扑 profiling

### 目标

在不改变任务和总请求数的情况下，比较不同 OpenClaw 部署拓扑的吞吐、时延长尾、CPU/内存/IO、session/history 开销和 vLLM/NPU 压力。

### 拓扑矩阵

| ID | 拓扑 | 关键 scenario 参数 | 目的 |
| --- | --- | --- | --- |
| A1 | 单容器单 Claw 单 worker | `instance_num=1`, `openclaw_num_per_instance=1`, `session_pool_size=1`, `max_in_flight=1` | 串行基线，测单请求端到端成本 |
| A2 | 单容器单 Claw 多 worker | `instance_num=1`, `openclaw_num_per_instance=1`, `session_pool_size=10/25/100`, `max_in_flight=100` | 测单 gateway 内 session、history、event loop 和 agent queue 压力 |
| A3 | 单容器多 Claw 实例 | `instance_num=1`, `openclaw_num_per_instance=2/4`, `max_in_flight=100` | 测同容器多 gateway 分流是否降低排队 |
| A4 | 多容器单 Claw 实例 | `instance_num=2/4`, `openclaw_num_per_instance=1` | 测容器隔离与多进程部署收益 |
| A5 | 多容器多 Claw 实例 | `instance_num=2/4`, `openclaw_num_per_instance=2/4` | 测最大横向扩展能力和 host 资源竞争 |
| A6 | 单 Claw 共享 session | `session_mode=shared`, `max_in_flight=100` | 测单 session 锁、history 放大和串行化瓶颈 |
| A7 | 单 Claw per-request session | `session_mode=per_request`, `max_in_flight=100` | 测去共享上下文后 gateway/session 文件压力 |

### 固定 workload

首批使用当前 task 作为轻量可复现 workload：

- `tasks/task_01_openclaw_comprehension.md`：轻量 LLM 请求，适合作为端到端 wait baseline。
- `tasks/task_00_context_inventory.md`：不依赖模型 key，可测 gateway/context 基础链路。
- 后续新增 `tasks/task_memory_short_context_probe.md` 和 `tasks/task_tool_call_probe.md`，分别服务实验 B/C。

### 建议 scenario 命名

- `scenarios/vllm/topology_a1_single_claw_serial_100.json`
- `scenarios/vllm/topology_a2_single_claw_burst_100_s10.json`
- `scenarios/vllm/topology_a2_single_claw_burst_100_s100.json`
- `scenarios/vllm/topology_a3_one_container_4claw_burst_100.json`
- `scenarios/vllm/topology_a4_four_container_1claw_burst_100.json`
- `scenarios/vllm/topology_a5_four_container_2claw_burst_100.json`
- `scenarios/vllm/topology_a6_single_claw_shared_session_100.json`
- `scenarios/vllm/topology_a7_single_claw_per_request_100.json`

### 采集指标

请求级：

- `connect_latency_ms`
- `send_latency_ms`
- `wait_latency_ms`
- `history_latency_ms`
- `total_latency_ms`
- success rate / error type
- `gateway_url` / `openclaw_index` / `instance_index`
- request window：首个 request start 到最后 request finish

系统级：

- 容器 CPU / memory / net IO：`docker_stats`
- gateway 进程 CPU / RSS / IO：`pidstat`
- event loop / fs / session trace：`node_trace`
- block IO await / util：`iostat`
- runnable queue / context switch / memory pressure：`vmstat`
- NPU utilization、显存、吞吐：`npu_smi`
- vLLM `/metrics`：prefill/decode tokens、queue time、TTFT、TPOT、KV cache、request queue

重点分析口径：

- throughput：`total_requests / request_window`
- p50 / p95 / p99：`send`、`wait`、`history`、`total`
- 长尾来源：`wait_p99` 还是 `history_p99`
- gateway 是否发生 session/history 锁竞争
- 单容器多 Claw 与多容器多 Claw 的 CPU cache、IO 和上下文切换差异
- OpenClaw 层排队与 vLLM 层排队是否同向增长

## 3. 实验 B：OpenClaw 与 Hermes 记忆机制 profiling

### 目标

比较 OpenClaw 与 Hermes 在短期上下文、长期记忆、多并发读写记忆场景下的负载特征，包括端到端时延、memory read/write 延迟、上下文膨胀、history 读写、索引/检索开销、并发一致性和错误率。

### 被测对象

| Agent | Transport | 需要扩展 |
| --- | --- | --- |
| OpenClaw | 现有 WebSocket gateway | 增加 memory seed/query/cleanup task，增加 memory trace 字段 |
| Hermes | 新增 Hermes transport 或通过 OpenClaw adapter 调 Hermes | 增加 `/hermes/v1/runs` 或对应入口，统一 result schema |

如果 Hermes 不能直接复用当前 gateway 协议，先新增 `client.transport = hermes_runs`，并在 runner 中实现同等阶段：

- `submit`：创建 Hermes run
- `wait`：等待 run 完成
- `history/result`：读取 run events / final output
- `memory_metrics`：解析 memory read/write/retrieval span

### 记忆 workload 设计

#### B1：短期上下文

目的：测同一 session 中上下文逐轮增加后的 latency 和 history 成本。

流程：

1. 在同一 session 中写入 5/10/20 轮事实。
2. 发起 query，要求引用前面第 N 条事实。
3. 并发放大：`session_pool_size=1/10/100`。
4. 对比 `history_limit=20/100/500`。

任务示例：

- `memory_short_write`: 写入明确 key-value，例如 `project_alpha_budget=71342`。
- `memory_short_query`: 查询某个 key，并要求只返回值。

#### B2：长期记忆写入

目的：测 memory write path 的吞吐和锁竞争。

流程：

1. 每个 request 写入一条带唯一 key 的事实。
2. `total_requests=100/300/500`。
3. 对比单 session、session pool、per-request session。
4. 运行后抽样验证记忆是否可读。

指标：

- memory write latency
- memory store size 增长
- memory index/update CPU
- memory 写失败或重复写
- cleanup 耗时

#### B3：长期记忆检索

目的：测 memory read / retrieval path 在并发下的性能。

流程：

1. 预先 seed 1k / 10k / 50k 条记忆。
2. 每个 request 查询一个 key 或相似语义事实。
3. 对比 OpenClaw 和 Hermes 的 retrieval latency、准确率和上下文注入 token 数。

指标：

- retrieval latency p50/p95/p99
- retrieved item count
- injected context tokens
- answer exact match
- memory cache hit/miss
- storage CPU / IO

#### B4：读写混合

目的：模拟真实多用户、多 session 同时读写记忆。

建议比例：

- 70% read / 30% write
- 50% read / 50% write
- 90% read / 10% write

关键观察：

- 写入是否阻塞读取。
- 长期记忆索引更新是否导致 p99 抬升。
- OpenClaw 与 Hermes 在共享记忆空间下是否出现跨 session 污染。

### 记忆隔离要求

每次 run 必须有独立 namespace：

- `memory_namespace = <scenario_name>-<run_id>`
- 运行前清理同名 namespace。
- 运行后导出 memory stats。
- 验证结束后按配置清理，或保留用于复盘。

必须记录：

- memory backend 类型
- memory namespace
- seed count
- final count
- cleanup status
- read/write span

## 4. 实验 C：多 agent / tool-calling 复杂环境 profiling

### 目标

比较 OpenClaw 与 Hermes 在多 agent 拓扑、工具调用、上下文传递、私有信息隔离、错误传播场景下的性能、资源和可靠性特征。

### 首选数据集：AgentCollabBench

用途：多 agent 协作与拓扑可靠性。

原因：

- 数据集本身定义 agent topology，包括 agents、directed edges、topology type、speaking order。
- 覆盖 `linear_chain`、`branching_tree`、`converging_dag`、`fully_connected`、`custom_graph`。
- 覆盖 `data_engineering`、`devops`、`swe` 三类任务。
- 有 `injections` 和 `ground_truth`，可以测 instruction decay、tracer durability、consensus pollution、cross-task leakage。
- 规模 900 条，适合抽样成 smoke、dev、full 三档。

来源：

- https://huggingface.co/datasets/AgentCollabBench/AgentCollabBench

### 辅助数据集：GAIA

用途：tool-calling / web / file / reasoning 复杂工具链。

使用方式：

- 选 Level 1/2 中工具需求明确、答案可自动匹配的子集。
- 不作为多 agent 拓扑主数据集，而作为 tool pressure workload。
- 重点测 tool call latency、工具错误、外部 IO、结果正确性。

来源：

- https://ai.meta.com/research/publications/gaia-a-benchmark-for-general-ai-assistants/
- https://huggingface.co/gaia-benchmark

### 可选后续数据集：SWE-bench Lite / Verified

用途：真实软件工程 issue 修复。

使用边界：

- 不作为第一阶段多 agent 协同数据集，因为原始 SWE-bench 不提供 agent topology。
- 适合后续测 coding agent 的 patch 生成能力、tool use、repo navigation、test execution。
- 正式接入需要调用 SWE-bench 官方 Docker evaluation harness，而不是只把 issue 文本塞进 `tasks/*.md`。

来源：

- https://github.com/SWE-bench/SWE-bench
- https://openai.com/index/introducing-swe-bench-verified/

### AgentCollabBench 接入设计

新增目录：

```text
datasets/
  agentcollabbench/
    raw/
    sampled/
    adapters/
```

新增 adapter：

```text
scripts/import_agentcollabbench.py
```

输入：

- `data/train.jsonl` 或 `TASK-*.json`

输出：

- `tasks/agentcollabbench/<task_id>.json`
- `scenarios/agentcollabbench/<topology>/<agent>/<task_id>_<topology>_<load>.json`

标准化 task schema：

```json
{
  "dataset": "agentcollabbench",
  "task_id": "TASK-SWE-CPR-059",
  "domain": "swe",
  "metric": "CPR",
  "topology_type": "linear_chain",
  "agents": [],
  "edges": [],
  "speaking_order": [],
  "injections": {},
  "ground_truth": {},
  "expected_turns": 0
}
```

### 多 agent runner 设计

新增 `client.task_format`：

- `prompt_md`：现有模式。
- `agentcollabbench_json`：多 agent 结构化任务。
- `gaia_json`：工具任务。
- `swebench_instance`：后续 SWE-bench 实例。

新增 `client.agent_backend`：

- `openclaw`
- `hermes`

新增 `client.orchestration_mode`：

- `single_orchestrator`：把整个拓扑压成一个 prompt，作为兼容 baseline。
- `simulated_multi_agent`：harness 按 topology 调用同一个 backend 的多个 session/role。
- `native_multi_agent`：OpenClaw/Hermes 原生支持 sub-agent 时，由 backend 负责调度，harness 只提交结构化 task。

第一阶段建议实现：

1. `single_orchestrator`：最快得到 baseline。
2. `simulated_multi_agent`：harness 控制 speaking order，便于 OpenClaw/Hermes 公平对比。
3. `native_multi_agent`：等两个系统都有稳定原生多 agent API 后再测。

### 多 agent 指标

性能指标：

- per-turn latency
- per-agent latency
- end-to-end latency
- tool call count / latency / error
- memory read/write count / latency
- inter-agent message size
- final context token count
- backend queue wait

可靠性指标：

- AgentCollabBench IDR：约束是否在 peer pressure 下衰减。
- RTD：tracer 经过多跳后是否保留。
- CPR：错误信念是否扩散到群体共识。
- CLC：Task A 私有上下文是否泄漏到 Task B。
- final answer rubric match。
- topology completion：是否完成所有 expected turns。

系统指标：

- gateway CPU / memory
- session/history fs IO
- memory store IO
- tool sandbox CPU / wall time
- vLLM queue / TTFT / TPOT
- NPU utilization / memory
- context switches / run queue

## 5. 实验矩阵总表

### 第一批：拓扑性能基线

| Batch | Dataset | Agent | Workload | Topology | Request |
| --- | --- | --- | --- | --- | --- |
| P1 | internal task_01 | OpenClaw | single prompt | A1-A7 | 100 |
| P2 | internal task_01 | OpenClaw | single prompt | A1-A7 | 300 |
| P3 | internal task_00 | OpenClaw | context command | A1-A7 | 500 |

### 第二批：记忆机制

| Batch | Dataset | Agent | Workload | Topology | Request |
| --- | --- | --- | --- | --- | --- |
| M1 | synthetic memory | OpenClaw | short context write/query | A2/A3/A4/A6/A7 | 100 |
| M2 | synthetic memory | Hermes | short context write/query | A2/A3/A4/A6/A7 | 100 |
| M3 | synthetic memory | OpenClaw | long memory read | A2/A3/A4 | 300 |
| M4 | synthetic memory | Hermes | long memory read | A2/A3/A4 | 300 |
| M5 | synthetic memory | OpenClaw/Hermes | 70/30 read-write mix | A2/A3/A4 | 300 |

### 第三批：多 agent / tool-calling

| Batch | Dataset | Agent | Workload | Topology | Request |
| --- | --- | --- | --- | --- | --- |
| C1 | AgentCollabBench smoke | OpenClaw | single_orchestrator | dataset topology + A2/A4 | 50 |
| C2 | AgentCollabBench smoke | Hermes | single_orchestrator | dataset topology + A2/A4 | 50 |
| C3 | AgentCollabBench dev | OpenClaw | simulated_multi_agent | linear/tree/dag/full | 100 |
| C4 | AgentCollabBench dev | Hermes | simulated_multi_agent | linear/tree/dag/full | 100 |
| C5 | GAIA subset | OpenClaw | tool-calling | A2/A4 | 50 |
| C6 | GAIA subset | Hermes | tool-calling | A2/A4 | 50 |

### 第四批：SWE-bench 后续

| Batch | Dataset | Agent | Workload | Topology | Request |
| --- | --- | --- | --- | --- | --- |
| S1 | SWE-bench Lite sample | OpenClaw | patch generation only | A2 | 10 |
| S2 | SWE-bench Lite sample | Hermes | patch generation only | A2 | 10 |
| S3 | SWE-bench Lite sample | OpenClaw/Hermes | official Docker eval | separate evaluator | 10-50 |

## 6. 需要新增的工程能力

### 6.1 Scenario schema 扩展

建议新增字段：

```json
{
  "client": {
    "transport": "openclaw_gateway",
    "agent_backend": "openclaw",
    "task_format": "prompt_md",
    "orchestration_mode": "single_request",
    "memory_namespace": "",
    "memory_setup_file": "",
    "tool_profile": true
  },
  "dataset": {
    "name": "",
    "split": "",
    "task_ids": [],
    "sample_size": 0
  }
}
```

兼容要求：

- 现有 scenario 不改也能运行。
- `task_format=prompt_md` 走现有 `effective_message()`。
- 新格式只在对应 runner 中启用。

### 6.2 Runner 扩展

新增 runner 层：

- `OpenClawGatewayRunner`：现有 WebSocket 流程。
- `HermesRunsRunner`：Hermes run submit/wait/result。
- `MultiAgentTopologyRunner`：读取 topology，按 speaking order 调用 backend。
- `ToolCallingProfiler`：解析 tool call spans。
- `MemoryProfiler`：解析 memory spans 和 memory stats。

### 6.3 Dataset adapter

需要新增：

- `scripts/import_agentcollabbench.py`
- `scripts/import_gaia_subset.py`
- `scripts/import_swebench_sample.py`
- `scripts/build_experiment_matrix.py`

输出要求：

- 每个导入任务都能追踪原始 dataset id。
- 生成的 scenario 名称包含 dataset、agent、topology、request 数、session 策略。
- 每个 scenario 写出 `dataset_meta`，方便后续报告聚合。

### 6.4 评分器

需要新增：

- `src/openclaw_harness/evaluators/agentcollabbench.py`
- `src/openclaw_harness/evaluators/memory.py`
- `src/openclaw_harness/evaluators/gaia.py`
- `src/openclaw_harness/evaluators/swebench.py`

第一阶段评分可以轻量实现：

- AgentCollabBench：正则/关键词检查 tracer、false belief、private token leakage。
- Memory：exact match。
- GAIA：exact match / normalized answer match。
- SWE-bench：patch-only 阶段只记录生成 patch；正式阶段交给官方 evaluator。

## 7. 运行与报告目录规范

建议目录：

```text
res/
  topology-profiling/
    run-001/
    summary.md
  memory-openclaw-hermes/
    run-001/
    summary.md
  agentcollabbench/
    smoke/
    dev/
    summary.md
  gaia-tooling/
    summary.md
  swebench/
    summary.md
```

每个 run 必须包含：

- `scenario.resolved.json`
- `preflight.json`
- `meta.json`
- `latency.csv`
- `summary.json`
- collector 原始数据和 summary
- `evaluation.json`
- `profile_summary.md`

跨 run 报告必须包含：

- topology 对比表
- latency p50/p95/p99
- throughput / request_window
- success/error rate
- resource peak/mean
- memory read/write/retrieval profile
- tool call profile
- dataset metric score
- 关键结论和下一步建议

## 8. 分阶段执行计划

### Phase 1：不改核心 runner，先完成拓扑 profiling

任务：

1. 从当前 `vps_docker_burst_task_01_100_session10.json` 派生 A1-A7 scenario。
2. 固定 `total_requests=100`，跑 `task_01_openclaw_comprehension`。
3. 开启 `docker_stats`、`pidstat`、`node_trace`、`iostat`、`vmstat`、`npu_smi`。
4. 生成 `res/topology-profiling/summary.md`。

成功标准：

- A1-A7 全部可运行。
- 每个 run 都有完整 latency 和 collector summary。
- 能解释 p95/p99 的主要来源。

### Phase 2：加入 synthetic memory workload

任务：

1. 新增短期上下文、长期记忆写入、长期记忆查询、读写混合任务。
2. 实现 memory namespace setup/cleanup。
3. 增加 memory exact-match evaluator。
4. 跑 OpenClaw baseline。
5. 增加 Hermes transport 后跑 Hermes 对照。

成功标准：

- 能分离 `send`、`wait`、`history` 和 memory read/write/retrieval 成本。
- 能比较 OpenClaw/Hermes 在同一任务、同一拓扑下的 p95/p99 和资源峰值。

### Phase 3：接 AgentCollabBench

任务：

1. 下载 AgentCollabBench。
2. 抽样 smoke set：每种 topology、每种 metric、每种 domain 至少 1 条。
3. 先跑 `single_orchestrator`。
4. 实现 `simulated_multi_agent`。
5. 增加 IDR/RTD/CPR/CLC 轻量评分。

成功标准：

- 能输出 topology-level latency/resource/reliability 对比。
- 能观察 fully connected / DAG / linear chain 对 tool/memory/context 压力的差异。

### Phase 4：接 GAIA tool-calling subset

任务：

1. 选择 Level 1/2 中答案可自动比对、工具链明确的任务。
2. 统一 tool trace 输出字段。
3. 对 OpenClaw/Hermes 分别跑 A2/A4 拓扑。

成功标准：

- 能统计 tool call 数、tool latency、tool error 和最终正确率。
- 能区分模型推理耗时与工具 IO 耗时。

### Phase 5：SWE-bench Lite / Verified 小样本

任务：

1. 先选 SWE-bench Lite 10 条作为 patch-only smoke。
2. OpenClaw/Hermes 生成 patch。
3. 接官方 Docker evaluator。
4. 扩到 50 条。

成功标准：

- 能把 agent 输出 patch 与 SWE-bench evaluator 对接。
- 报告 resolved rate、patch generation latency、test runtime、失败类型。

## 9. 优先级建议

第一优先级：

- A1-A7 拓扑 profiling。
- Synthetic memory workload。
- OpenClaw/Hermes transport 对齐。

第二优先级：

- AgentCollabBench adapter。
- Simulated multi-agent runner。
- 多 agent 指标和评分。

第三优先级：

- GAIA tool-calling subset。
- SWE-bench Lite official evaluator。

不建议一开始就直接上 SWE-bench full 或 AgentCollabBench full。先跑 small smoke，确认 trace、评分和报告链路稳定，再扩大规模。

## 10. 最小下一步

建议下一步直接做四件事：

1. 生成 A1-A7 的 100 request scenario。
2. 写 `scripts/run_topology_matrix.py` 批量执行。
3. 新增 `tasks/memory_*` synthetic workload。
4. 在 runner 输出里增加 `request_window` 和按 `gateway_url/openclaw_index/instance_index` 的分组汇总。

完成这四项后，就可以开始回答第一个核心问题：同样 100 个 burst request 下，单 Claw、多 worker、单容器多 Claw、多容器多 Claw 的吞吐、p95/p99、CPU/IO/session/history 瓶颈分别在哪里。
