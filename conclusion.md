# OpenClaw Gateway 请求链路与 Multi 变慢归因结论

本文把当前 `client-harness` 仓库里已经确认的结论整理成一份可复用的说明，重点回答两个问题：

1. 一条请求发送到 gateway 之后，内部处理顺序大致是什么样。
2. 为什么 `multi` 场景会明显比 `single` 更慢，到底是谁在拖慢。

## 结论摘要

当前最重要的结论有四条：

1. `client-harness` 的一次完整请求链路是 `chat.send -> agent.wait -> chat.history`。
2. 进入 gateway 之后，`agent.wait` 期间会先做 `bootstrap/context bundle`，再做 `skills/context/system prompt` 相关处理，然后进入 `reply dispatch`，最后写终态并结束 `wait`。
3. `multi` 变慢的主因，不是模型推理，也不是磁盘裸 `read`/`write` syscall 变慢，而是并发下 `session manager` 相关共享状态链路更重，包括：
   `sessions/` 目录解析、`sessions.json.lock`、`sessions.json.<tmp>` 临时文件链、`sessions.json` 更新，以及它们占用的异步文件系统执行通道。
4. `bootstrap_load_mean_ms` 在 `multi` 下更高，主要不是因为 steady-state 的 bootstrap 读操作本身变慢，而是因为 `multi` 有更多 `per_worker session`，导致“每个 session 的第一次冷启动”被重复了 10 次。

## 本文使用的数据来源

主证据来自以下文件：

- `500 full` 对比报告：
  [res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/summary.md](res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/summary.md)
- `500 full` 原始 gateway span：
  [out/20260325T174736Z_vps-docker-multi-task-00-500-10x50/gateway_runtime_spans.parsed.csv](out/20260325T174736Z_vps-docker-multi-task-00-500-10x50/gateway_runtime_spans.parsed.csv)
- `500 full` 原始 node trace：
  [out/20260325T174736Z_vps-docker-multi-task-00-500-10x50/node_trace.parsed.csv](out/20260325T174736Z_vps-docker-multi-task-00-500-10x50/node_trace.parsed.csv)
- 埋点说明：
  [span_points.md](span_points.md)
- client 侧调用顺序代码：
  [src/openclaw_harness/runner.py](src/openclaw_harness/runner.py)
  [src/openclaw_harness/gateway_client.py](src/openclaw_harness/gateway_client.py)
- 场景配置：
  [scenarios/vps/vps_docker_single.json](scenarios/vps/vps_docker_single.json)
  [scenarios/vps/vps_docker_multi_10x50.json](scenarios/vps/vps_docker_multi_10x50.json)

交叉验证使用：

- `his1` 对比报告：
  [res/vps-docker-single-task-his1-50-full-vs-vps-docker-multi-task-his1-00-50-full/summary.md](res/vps-docker-single-task-his1-50-full-vs-vps-docker-multi-task-his1-00-50-full/summary.md)

说明：

- `his1` 这组结果只有延迟和系统层面的交叉验证价值。
- `his1` 报告里的 `Gateway Runtime Stage Table` 和 `Node Focus Groups Table` 是空的，所以本文的细粒度链路和归因，主要还是依赖 `500 full` 这组。
- `his1` 两边总请求数也不相同：
  `single = 100`
  `multi = 50`
  因此它只能作为辅助对照，不能替代 `500 full` 这组主证据。

## 关键词与术语解释

| 术语 | 中文解释 | 在本文里的具体含义 |
| --- | --- | --- |
| `gateway` | 网关服务 | 接收 `chat.send`、`agent.wait`、`chat.history` 的服务端 |
| `run_id` | 运行标识 | 一次请求或一次内部执行流程的唯一标识 |
| `session_key` | 会话键 | 同一会话的稳定标识；一个 worker 或多个请求可以复用 |
| `per_worker session` | 每个 worker 一个会话 | 当前场景里，同一个 worker 的多次请求会落到同一个 session |
| `bootstrap` | 启动上下文装配 | 构建 system prompt 前，加载/检查一组 workspace 基础文件 |
| `workspace bootstrap files` | 工作区基础文件 | `AGENTS.md`、`SOUL.md`、`TOOLS.md`、`IDENTITY.md`、`USER.md`、`HEARTBEAT.md`、`BOOTSTRAP.md` |
| `context bundle` | 上下文打包 | 把 bootstrap、skills、tools、prompt params、system prompt 相关内容拼起来 |
| `skills` | 技能上下文 | OpenClaw 在构建 prompt 时纳入的技能信息来源 |
| `reply dispatch` | 回复分发 | 内部结果准备好后，进入回复队列并发回客户端的阶段 |
| `admission wait` | 准入等待 | `agent.wait` 开始后，到内部执行真正进入 `reply_start` 之前的等待时间 |
| `session manager` | 会话状态管理器 | 负责 session 索引、状态目录、会话文件更新的那部分逻辑 |
| `cold start` | 冷启动 | 某个 session 第一次请求时，需要做的首次初始化成本 |
| `steady-state` | 稳态 | 同一 session 已经热起来之后，后续请求的常态成本 |
| `node fs async` | Node 异步文件系统操作 | 走 libuv worker 的异步 FS span，不等于裸 syscall 时间 |

## 客户端视角的外层请求链路

`client-harness` 的每条请求，外层固定执行三步：

1. `chat.send`
2. `agent.wait`
3. `chat.history`

对应代码见：

- [src/openclaw_harness/runner.py](src/openclaw_harness/runner.py)
- [src/openclaw_harness/gateway_client.py](src/openclaw_harness/gateway_client.py)

可以把这三步理解成：

- `chat.send`：把请求提交给 gateway。
- `agent.wait`：等待 gateway/agent 内部真正执行完。
- `chat.history`：执行完以后，把会话里的消息历史取回来。

## 请求进入 Gateway 后的内部处理顺序

这一部分分成两层说明。

第一层是“按埋点设计应有的顺序”：

1. `chat.send` 进入 gateway。
2. gateway 在 `chat_send_span` 里做 `ack`、`dispatch_start`。
3. 客户端随后调用 `agent.wait(run_id)`。
4. gateway 开始 `agent_wait_span`。
5. 内部 embedded 执行链开始。
6. 执行 `bootstrap/context bundle/skills/system prompt`。
7. 生成 reply。
8. 进入 `reply_dispatch_span` 队列。
9. 写终态，结束 `agent.wait`。

这部分来自埋点说明：

- [span_points.md](span_points.md)

第二层是“当前日志里直接能看到的顺序”。

在 `gateway_runtime_spans.parsed.csv` 里，当前能稳定看到的顺序大致是：

1. `agent_wait_span.wait_start`
2. `agent_wait_span.wait_race_start`
3. `embedded_run_span.reply_start`
4. `embedded_run_span.inline_actions_start`
5. `embedded_run_span.inline_command_dispatch_start`
6. `embedded_run_span.context_reply_start`
7. `embedded_run_span.context_report_start`
8. `embedded_run_span.context_bundle_start`
9. `embedded_run_span.context_bundle_resolve_start`
10. `embedded_run_span.context_bundle_bootstrap_start`
11. `embedded_run_span.bootstrap_context_start`
12. `embedded_run_span.bootstrap_load_start`
13. `embedded_run_span.bootstrap_load_end`
14. `embedded_run_span.bootstrap_filter_start/end`
15. `embedded_run_span.bootstrap_hooks_start/end`
16. `embedded_run_span.bootstrap_sanitize_start/end`
17. `embedded_run_span.bootstrap_context_files_start/end`
18. `embedded_run_span.bootstrap_context_end`
19. `embedded_run_span.context_bundle_bootstrap_end`
20. `embedded_run_span.context_bundle_skills_start`
21. `embedded_run_span.skills_snapshot_start`
22. `embedded_run_span.skills_entries_start`
23. `embedded_run_span.skills_merge_start`
24. 多个 `embedded_run_span.skills_source_start/end`
25. `embedded_run_span.skills_metadata_start/end`
26. `embedded_run_span.skills_filter_start/end`
27. `embedded_run_span.skills_prompt_start/end`
28. `embedded_run_span.skills_snapshot_end`
29. `embedded_run_span.context_bundle_skills_end`
30. `embedded_run_span.context_bundle_tools_start/end`
31. `embedded_run_span.context_bundle_prompt_params_start/end`
32. `embedded_run_span.context_bundle_system_prompt_start/end`
33. `embedded_run_span.context_bundle_resolve_end`
34. `embedded_run_span.context_bundle_end`
35. `embedded_run_span.context_report_end`
36. `embedded_run_span.context_reply_end`
37. `embedded_run_span.inline_command_dispatch_end`
38. `embedded_run_span.inline_actions_end`
39. `embedded_run_span.inline_actions_reply`
40. `embedded_run_span.reply_end`
41. `reply_dispatch_span.queue_enter`
42. `reply_dispatch_span.queue_acquired`
43. `reply_dispatch_span.queue_idle`
44. `agent_wait_span.dedupe_terminal_write`
45. `agent_wait_span.wait_first_source`
46. `agent_wait_span.wait_complete`

说明：

- 当前 `gateway_runtime_spans` 里，外层 request 的 `run_id` 和内层 embedded 执行的 `run_id` 不总是相同。
- 但按 `session_key` 排序后，顺序关系是稳定且清楚的。
- 也就是说，链路顺序本身是可以从日志里直接恢复出来的。

## 一个实际样本的阶段展开

在 `multi` 的 `agent:main:vps-docker-multi-task-00-500-10x50-w1` 上，可以看到一次典型请求里：

- `bootstrap_load_end = 605ms`
- `context_bundle_bootstrap_end = 634ms`
- `context_bundle_skills_end = 1115ms`
- `context_bundle_end = 1792ms`
- `reply_end = 1967ms`
- `reply_dispatch` 队列只额外花了大约 `3ms`

这说明：

- 主要时间花在 `context bundle` 构建，而不是 `reply dispatch` 队列。
- 其中 `bootstrap` 是 `context bundle` 的前半段。
- 但 `skills/context bundle` 的贡献要比单次 `bootstrap_load` 更大。

## 为什么 Multi 更慢：归因树

### 根结论

`multi` 更慢，主因不是模型变慢，也不是 `reply_dispatch` 队列明显变长，而是：

1. `multi` 场景有更多 `session`，所以重复触发了更多次 session 首次冷启动。
2. 并发下 `session manager` 的共享状态链路更重，放大了 `agent.wait` 早期阶段和异步 FS 通道拥堵。

### 归因树

根节点：`wait_mean_ms` 大幅升高

- `single`: `973.591ms`
- `multi`: `10082.269ms`

分支 A：不是主要矛盾的部分

- `skills_mean_ms` 基本没变：
  `698.850ms -> 700.802ms`
- `context_bundle_mean_ms` 只小幅增加：
  `742.934ms -> 764.308ms`
- `reply_dispatch_queue_wait_mean_ms` 基本没变：
  `0.002ms -> 0.002ms`
- `reply_dispatch_queue_hold_mean_ms` 基本没变：
  `0.003ms -> 0.003ms`

说明：

- `reply dispatch` 不是主要瓶颈。
- 技能系统本身也不是主要瓶颈。

分支 B：明确变重的部分

- `execution_admission_wait_mean_ms`：
  `0.143ms -> 9.253ms`
- `sessions_lock_total_ms`：
  `298.634ms -> 733.853ms`
- `sessions_dir_enum_total_ms`：
  `77.678ms -> 1781.805ms`
- `sessions_tmp_total_ms`：
  `327.700ms -> 1679.839ms`
- `sessions_json_total_ms`：
  `164.106ms -> 210.497ms`
- `node_fs_async_mean_ms`：
  `143.511ms -> 201.681ms`

说明：

- 真正变重的是 session 状态目录和索引更新这条链。
- 并发下，这条链会占用共享的异步文件系统执行通道。
- 这会把“执行真正开始之前”的等待，也就是 `admission wait` 拉高。

分支 C：`bootstrap` 为什么也更慢

这是最容易误解的一点。

现象上看：

- `gateway bootstrap_load_mean_ms`：
  `2.758ms -> 22.000ms`
- `workspace_bootstrap` 路径分类累计时长：
  `6459.129ms -> 8091.316ms`

如果只看均值，很容易误以为是“multi 把 bootstrap 读文件本身拖慢了”。但进一步拆开以后，发现更准确的解释是：

1. `multi` 不是 1 个 session，而是 10 个 session。
2. 当前场景是 `per_worker`。
3. `single` 只有 1 个 worker，所以只有 1 个 session 首次冷启动。
4. `multi` 有 10 个 worker，所以有 10 个 session 首次冷启动。

### 冷启动数据

从 `gateway_runtime_spans.parsed.csv` 里直接统计 `embedded_run_span.bootstrap_load_end`：

`single`

- 总样本数：`500`
- 平均值：`2.758ms`
- 大于 `100ms` 的样本数：`1`
- 唯一明显冷启动样本：`126ms`

`multi`

- 总样本数：`500`
- 平均值：`22.000ms`
- 大于 `100ms` 的样本数：`10`
- 大于 `200ms` 的样本数：`10`
- 大于 `500ms` 的样本数：`5`
- 10 个 session 的首次样本分别约为：
  `213ms`、`257ms`、`274ms`、`328ms`、`337ms`、`605ms`、`1491ms`、`1516ms`、`2337ms`、`2421ms`

### 去掉每个 Session 的第一次请求以后

这是最关键的对照。

从同一份 `gateway_runtime_spans.parsed.csv` 里，去掉每个 `session_key` 的第一条 `bootstrap_load_end` 后：

- `single` 的 bootstrap 均值：`2.511ms`
- `multi` 的 bootstrap 均值：`2.492ms`

结论：

- steady-state 下，`bootstrap` 基本没有变慢。
- `bootstrap_load_mean_ms` 在 `multi` 下变高，主要是均值被更多次冷启动拉高。
- 因此，`bootstrap` 不是 `multi` 变慢的主因；它主要是“多 session 冷启动”的伴生放大项。

## 为什么“纯读取 bootstrap 文件”也会表现得更慢

这里要区分两层时间：

第一层：裸 syscall 时间

在 `500 full` 报告里：

- `read` 平均时长约 `0.022ms`
- `write` 平均时长约 `0.030ms`

single 和 multi 基本一样。

这说明：

- 磁盘裸 `read/write` syscall 本身并没有明显变慢。

第二层：Node 异步 FS span 时间

`node_trace` 里的 `duration_ms`，不是裸 syscall 时间，而是一次异步 FS 操作从开始到结束回调之间的整段时间。

也就是说，这个时间里可能包含：

- libuv worker 排队
- 实际 syscall
- 回调回到主线程的等待
- 事件循环调度

因此，即便某个操作在语义上只是“检查文件”或“打开文件”，在 trace 里也可能体现为十几毫秒。

## 原始 Trace 证明了什么

从 `multi` 的原始 `node-trace-*.json` 和 `node_trace.parsed.csv` 里，可以直接看到：

bootstrap 路径命中的主要操作，不是写入，而是：

- `access`
- `open`

例如：

- `HEARTBEAT.md`
- `USER.md`
- `IDENTITY.md`
- `TOOLS.md`

命中的主要就是 `access/open`。

而 session 这条链明显不是纯读，它包括：

- `sessions.json.lock`：`open`、`lstat`、`unlink`
- `sessions.json.<uuid>.tmp`：`open`、`chmod`、`lstat`

这说明：

- `workspace bootstrap files` 本身更像“检查 + 打开”。
- `session manager` 那条链则包含锁文件和临时文件写链。

## 原始 Node Trace 的关键数值

以下数值来自 `500 full` 原始 `node_trace.parsed.csv` 的同口径汇总：

bootstrap 文件相关：

- `HEARTBEAT.md access`
  `single_mean = 9.140ms`
  `multi_mean = 13.305ms`
- `USER.md access`
  `single_mean = 10.973ms`
  `multi_mean = 15.025ms`
- `IDENTITY.md access`
  `single_mean = 12.805ms`
  `multi_mean = 16.767ms`
- `TOOLS.md access`
  `single_mean = 14.634ms`
  `multi_mean = 18.489ms`

session 链路相关：

- `sessions.json.lock open`
  `single_mean = 1.163ms`
  `multi_mean = 7.537ms`
- `sessions tmp lstat`
  `single_mean = 1.235ms`
  `multi_mean = 10.142ms`
- `sessions tmp chmod`
  `single_mean = 1.171ms`
  `multi_mean = 3.493ms`

这组数说明：

- `bootstrap access/open` 确实在 `multi` 下变慢了。
- 但更夸张的是 session 相关链路。
- 因此，bootstrap 变慢更像是“共享异步 FS 通道被 session 链路挤占后的连带后果”，而不是它自身是根因。

## 单句结论

如果只用一句话总结：

`multi` 更慢，核心原因是“10 个 per-worker session 带来的 10 次冷启动 + 并发下 session manager 共享状态链路拥堵”；`bootstrap` 在均值上变慢主要是冷启动数量变多，以及共享 async FS 通道被挤占后的次级效应，而不是 steady-state 的 bootstrap 读文件本身变成了主要瓶颈。

## 重要图表与推荐阅读顺序

建议先看下面这些图表和表：

1. 端到端延迟总览：
   [res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/figures/latency_overview.png](res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/figures/latency_overview.png)
2. gateway 各阶段时间线：
   [res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/figures/gateway_runtime_timeline.png](res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/figures/gateway_runtime_timeline.png)
3. node focus groups 对比：
   [res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/figures/node_focus_group_duration_ms.png](res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/figures/node_focus_group_duration_ms.png)
4. node focus 时间线：
   [res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/figures/node_focus_timeline.png](res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/figures/node_focus_timeline.png)
5. Node 异步运行时均值：
   [res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/figures/node_runtime_mean_duration_ms.png](res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/figures/node_runtime_mean_duration_ms.png)
6. 路径分类分布：
   [res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/figures/runtime_category_pct.png](res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/figures/runtime_category_pct.png)

补充交叉验证：

7. `his1` 延迟总览：
   [res/vps-docker-single-task-his1-50-full-vs-vps-docker-multi-task-his1-00-50-full/figures/latency_overview.png](res/vps-docker-single-task-his1-50-full-vs-vps-docker-multi-task-his1-00-50-full/figures/latency_overview.png)

`his1` 的延迟层面仍然支持“multi 更慢”这个高层结论：

- `wait_mean_ms`
  `539.512 -> 6054.566`
- `total_mean_ms`
  `626.935 -> 6088.424`

## 还需要注意的限制

1. 当前 `gateway_runtime_spans` 里没有被单独导出 `chat_send_span` 的完整表，因此 `chat.send` 进入 gateway 的最前段，本文主要依据埋点说明和整体顺序推断。
2. 当前外层 request `run_id` 和内层 embedded `run_id` 不总是相同，所以在恢复链路时要优先按 `session_key` 看顺序。
3. `his1` 这组结果缺少 gateway/node 细粒度阶段表，因此只能作为延迟层面的交叉验证，不适合作为主要归因依据。
4. `his1` 报告目录名里是 `multi-task-his1-00-50-full`，而场景文件名是 `vps_docker_multi_his1.json`，场景名本身是 `vps-docker-multi-task-his1-50-full`。这说明该组结果在命名上存在不一致，引用时要以具体文件内容为准。

## 推荐下一步

如果后续还要继续验证，最值得做的不是重复看均值，而是继续做下面两类实验：

1. 保持总请求数不变，但把 `session_mode` 改成 `shared` 或 `per_request`，验证“session 数量变化”对 `bootstrap_load_mean_ms` 的影响。
2. 单独把每个 `session_key` 的第一次请求标出来，区分 `cold start` 和 `steady-state`，避免把它们混在总均值里。
