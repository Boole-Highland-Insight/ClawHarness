# 实验计划与结果记录

更新时间：2026-04-14

说明：

- 本文基于当前仓库里已有的 `out/`、`res/`、`conclusion.md` 整理。
- 第一部分只看大类是否完成；第二部分按参数维度持续补充实验记录。
- 这里的 `single` / `multi` 默认分别对应 `500 * 1w` / `50 * 10w`。
- 当前 `req_pause` 统一按 `0ms` 记录。
- `single` 场景下 `stagger` 基本没有实际影响，保留该列只是为了和 `multi` 对齐。

## 1. 总体计划

| 角度 | gateway | Gateway + vllm |
| --- | --- | --- |
| 单实例多 session | ✅ | ⬜ |
| 单实例多 agent | ⬜ | ⬜ |
| 多实例多 session | ⬜ | ⬜ |

## 2. 详细参数、实验记录与简短结论

补充说明：

- 单实例多 agent 目前只有总体规划，还没有稳定的参数矩阵，等方案明确后再单独补表。
- 当前已完成的大类主要是“单实例多 session / gateway only”，其中 `hw cloud` 的 `worker / request / shared` 组合已补齐。

### 2.1 单实例多 session - gateway only

| 机器 | 单线程/多线程 | 任务/并发数 | 模式 | stagger | req_pause | total_mean | 完成 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hw cloud | single | 500 * 1w | worker | 0ms | 0ms | 256.46ms | ✅ | `light` 最新自动化复跑；作为 single 基线 |
| hw cloud | single | 500 * 1w | request | 0ms | 0ms | 372.65ms | ✅ | 明显高于 `worker` / `shared` |
| hw cloud | single | 500 * 1w | shared | 0ms | 0ms | 256.93ms | ✅ | 与 `worker` 几乎持平，当前未见明显共享 session 额外成本 |
| hw cloud | multi | 50 * 10w | worker | 150ms | 0ms | 1904.32ms | ✅ | 最新自动化复跑；作为 multi 主基线 |
| hw cloud | multi | 50 * 10w | worker | 300ms | 0ms | 1864.99ms | ✅ | 与 `150ms` 接近，这次略好约 `39ms` |
| hw cloud | multi | 50 * 10w | request | 150ms | 0ms | 3203.40ms | ✅ | 三种模式里最慢，显著高于 `worker` |
| hw cloud | multi | 50 * 10w | request | 300ms | 0ms | 3289.08ms | ✅ | 比 `150ms` 略差，stagger 改善有限 |
| hw cloud | multi | 50 * 10w | shared | 150ms | 0ms | 2034.35ms | ✅ | 介于 `worker` 和 `request` 之间 |
| hw cloud | multi | 50 * 10w | shared | 300ms | 0ms | 2183.21ms | ✅ | 比 `150ms` 略差约 `149ms` |
| local | single | 500 * 1w | worker | 0ms | 0ms | - | ⬜ | 待补，本地对照建议先复用 WSL + Docker 口径 |
| local | multi | 50 * 10w | worker | 150ms | 0ms | - | ⬜ | 待补 |
| local | single | 500 * 1w | request | 0ms | 0ms | - | ⬜ | 待补 |
| local | multi | 50 * 10w | request | 150ms | 0ms | - | ⬜ | 待补 |
| local | multi | 50 * 10w | shared | 150ms | 0ms | - | ⬜ | 待补 |
| 910c | single | 500 * 1w | worker | 0ms | 0ms | - | ⬜ | 待补 |
| 910c | multi | 50 * 10w | worker | 150ms | 0ms | - | ⬜ | 待补 |
| 910c | single | 500 * 1w | request | 0ms | 0ms | - | ⬜ | 待补 |
| 910c | multi | 50 * 10w | request | 150ms | 0ms | - | ⬜ | 待补 |
| 910c | multi | 50 * 10w | shared | 150ms | 0ms | - | ⬜ | 待补 |

简短结论：

- 最新自动化复跑的 9 组 `hw cloud / gateway only` 结果已补齐，且全部 `500/500` 成功。
- `per_worker` 下，`single -> multi` 的 `total_mean` 仍有明显跃升：`256.46ms -> 1904.32ms / 1864.99ms`，退化趋势稳定存在。
- `per_request` 仍然最慢：`single` 为 `372.65ms`，`multi` 为 `3203.40ms / 3289.08ms`；`shared` 在 `multi` 下介于 `worker` 与 `request` 之间。
- `single` 下 `shared` 与 `worker` 几乎持平；当前更像是并发场景下的共享状态路径成为瓶颈，而不是“共享 session”本身在低并发下就有明显固定成本。
- `stagger 150ms / 300ms` 的影响整体有限，且不同模式下优劣不完全一致，暂时看不到稳定、可复用的改善方向。

### 2.2 单实例多 session - Gateway + vllm

| 机器 | 单线程/多线程 | 任务/并发数 | 模式 | stagger | req_pause | total_mean | 完成 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hw cloud | single | 500 * 1w | worker | 0ms | 0ms | - | ⬜ | 建议先做基线，和 gateway only 对齐 |
| hw cloud | multi | 50 * 10w | worker | 150ms | 0ms | - | ⬜ | 待补，优先和 gateway only 主对比保持同口径 |
| hw cloud | multi | 50 * 10w | worker | 300ms | 0ms | - | ⬜ | 待补，保留 stagger 对照 |
| hw cloud | single | 500 * 1w | request | 0ms | 0ms | - | ⬜ | 待补 |
| hw cloud | multi | 50 * 10w | request | 150ms | 0ms | - | ⬜ | 待补 |
| hw cloud | multi | 50 * 10w | shared | 150ms | 0ms | - | ⬜ | 待补 |
| local | single | 500 * 1w | worker | 0ms | 0ms | - | ⬜ | 待补 |
| local | multi | 50 * 10w | worker | 150ms | 0ms | - | ⬜ | 待补 |
| local | multi | 50 * 10w | shared | 150ms | 0ms | - | ⬜ | 待补 |
| 910c | single | 500 * 1w | worker | 0ms | 0ms | - | ⬜ | 待补 |
| 910c | multi | 50 * 10w | worker | 150ms | 0ms | - | ⬜ | 待补 |
| 910c | multi | 50 * 10w | shared | 150ms | 0ms | - | ⬜ | 待补 |

简短结论：

- 暂无结果。
- 建议先复用 gateway only 的 `worker -> request -> shared` 顺序，先在 `hw cloud` 做出第一套基线，再扩到 `local` 和 `910c`。

### 2.3 多实例多 session - gateway only

| 机器 | 单线程/多线程 | 任务/并发数 | 模式 | stagger | req_pause | total_mean | 完成 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hw cloud | single | 500 * 1w | worker | 0ms | 0ms | - | ⬜ | 待补，多实例下的 single 先做基线 |
| hw cloud | multi | 50 * 10w | worker | 150ms | 0ms | - | ⬜ | 待补，和单实例多 session 做正交对比 |
| hw cloud | multi | 50 * 10w | worker | 300ms | 0ms | - | ⬜ | 待补 |
| hw cloud | single | 500 * 1w | request | 0ms | 0ms | - | ⬜ | 待补 |
| hw cloud | multi | 50 * 10w | request | 150ms | 0ms | - | ⬜ | 待补 |
| hw cloud | multi | 50 * 10w | shared | 150ms | 0ms | - | ⬜ | 待补 |
| local | single | 500 * 1w | worker | 0ms | 0ms | - | ⬜ | 待补 |
| local | multi | 50 * 10w | worker | 150ms | 0ms | - | ⬜ | 待补 |
| local | multi | 50 * 10w | shared | 150ms | 0ms | - | ⬜ | 待补 |
| 910c | single | 500 * 1w | worker | 0ms | 0ms | - | ⬜ | 待补 |
| 910c | multi | 50 * 10w | worker | 150ms | 0ms | - | ⬜ | 待补 |
| 910c | multi | 50 * 10w | shared | 150ms | 0ms | - | ⬜ | 待补 |

简短结论：

- 暂无结果。
- 该组建议优先观察“实例数扩展后，session 相关共享状态是否下沉到实例内局部，还是转移到新的全局瓶颈”。

### 2.4 多实例多 session - Gateway + vllm

| 机器 | 单线程/多线程 | 任务/并发数 | 模式 | stagger | req_pause | total_mean | 完成 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hw cloud | single | 500 * 1w | worker | 0ms | 0ms | - | ⬜ | 待补，先做最小基线 |
| hw cloud | multi | 50 * 10w | worker | 150ms | 0ms | - | ⬜ | 待补 |
| hw cloud | multi | 50 * 10w | worker | 300ms | 0ms | - | ⬜ | 待补 |
| hw cloud | single | 500 * 1w | request | 0ms | 0ms | - | ⬜ | 待补 |
| hw cloud | multi | 50 * 10w | request | 150ms | 0ms | - | ⬜ | 待补 |
| hw cloud | multi | 50 * 10w | shared | 150ms | 0ms | - | ⬜ | 待补 |
| local | single | 500 * 1w | worker | 0ms | 0ms | - | ⬜ | 待补 |
| local | multi | 50 * 10w | worker | 150ms | 0ms | - | ⬜ | 待补 |
| local | multi | 50 * 10w | shared | 150ms | 0ms | - | ⬜ | 待补 |
| 910c | single | 500 * 1w | worker | 0ms | 0ms | - | ⬜ | 待补 |
| 910c | multi | 50 * 10w | worker | 150ms | 0ms | - | ⬜ | 待补 |
| 910c | multi | 50 * 10w | shared | 150ms | 0ms | - | ⬜ | 待补 |

简短结论：

- 暂无结果。
- 建议最后做这一组，避免把“多实例影响”和“vllm 引入影响”叠在一起后难以归因。


## 项目总结 / Project Summary

### 中文

**项目是什么：** 这是 **OpenClaw Gateway 的负载测试工具**（`client-harness`），用 Python 编写。它通过 WebSocket API 驱动 OpenClaw gateway 的 `chat.send → agent.wait → chat.history` 请求链路，采集延迟、CPU/内存、磁盘 IO 等指标。

**测了什么：** 核心对比是 **单线程 vs 多线程（并发）场景下 gateway 的性能退化**：
- **单线程（single）**：1 个 worker 顺序发 500 个请求
- **多线程（multi）**：10 个 worker 各发 50 个请求（并发）
- 使用 `/context list` 命令（不依赖模型 API），在 VPS Docker 环境上运行
- 还测试了不同参数维度：`per_worker` vs `per_request` session 模式、不同 stagger 间隔（0/150/300ms）、full vs light 采集模式

**核心结论：**
1. **multi 场景明显比 single 慢**——`wait` 阶段均值从约 1s 拉高到约 10s
2. **瓶颈不是模型推理，而是 session manager 的共享状态路径**：`sessions/` 目录解析、`sessions.json.lock` 文件锁、临时文件链等在并发下成为热点
3. stagger（错峰启动）只能轻微改善，不能根治 multi 退化

---

### English

**What it is:** A Python **load-testing harness for OpenClaw Gateway**. It drives the gateway's `chat.send → agent.wait → chat.history` pipeline via WebSocket, collecting latency, CPU/memory, and disk IO metrics.

**What was tested:** The core comparison is **single-threaded vs multi-threaded (concurrent) gateway performance**:
- **Single**: 1 worker, 500 sequential requests
- **Multi**: 10 workers × 50 requests (concurrent)
- Uses the `/context list` command (model-free) on a VPS Docker setup
- Also varied: `per_worker` vs `per_request` session modes, stagger intervals (0/150/300ms), full vs light collection

**Key findings:**
1. **Multi is significantly slower than single** — `wait` mean jumps from ~1s to ~10s
2. **The bottleneck is not model inference but the session manager's shared-state path**: `sessions/` directory parsing, `sessions.json.lock`, temp file chains become hot spots under concurrency
3. Staggering worker starts provides only marginal improvement, not a fix for multi degradation
