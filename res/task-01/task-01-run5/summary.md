# OpenClaw/Hermes 并发部署总结

本文基于 `/root/client-harness/res/task-01/task-01-run5/` 下已经生成的结果文件，重点回答四个问题：

1. 为什么 OpenClaw 的 Gateway 与 session 管理机制会在多会话并发下成为瓶颈。
2. 单实例串行、单实例多会话、多实例、并行多容器等部署模型如何影响吞吐、延迟、尾延和资源利用率。
3. 为什么 Host / Container / Instance / Worker 分层编排比单纯增加 OpenClaw 实例数更重要。
4. 在 Ascend 910C 且 vLLM 与 OpenClaw/Hermes 同机部署时，推荐怎样设置 Host、Container、Instance 和 Worker。

## 结论摘要

`task-01-run5` 的核心结论是：OpenClaw/Hermes 的并发扩展不是“实例越多越好”，而是要控制 Gateway、session store、history 读写、agent wait 调度和 vLLM 后端之间的排队关系。单实例串行的单请求体验最好、资源最低，但整批完成最慢；单实例 4 会话并发显著提升整批吞吐，但会增加 `wait` 阶段和尾延；把多个实例堆在同一个容器里并不稳定，容易把 session/history 长尾放大；多容器隔离通常比单容器多实例更适合作为横向扩展边界。

从 `最终版本` 对比看，单实例串行的 `request_window` 为 `1071.6s`，`total_mean` 为 `10.7s`，`P95` 为 `11.6s`，`overall_output_tps` 为 `18.7`，资源最低。单实例 4 会话并发把 `request_window` 缩短到 `466.8s`，吞吐升到 `30.9 output tokens/s`，但 `total_mean` 升到 `15.8s`，`P99` 升到 `40.6s`。单容器 4 实例并行的 `request_window` 为 `557.2s`，`P95/P99` 为 `34.3s / 47.1s`，RSS 约 `2.0 GiB`，说明在一个容器内堆实例会放大状态和资源竞争。4 容器单实例并行的 `request_window` 降到 `406.9s`，`total_mean` 为 `11.4s`，`P99` 为 `24.1s`，但 CPU 升到 `57%`、RSS 约 `2.2 GiB`，磁盘写入也明显增加。

如果只看 run5 里更激进的组合，`2 containers x 2 instances x 1 worker` 且 `500ms stagger` 的 `request_window` 最短，为 `338.2s`，`P95/P99` 为 `15.5s / 27.2s`；但它的 CPU 和 RSS 显著高于单实例多会话，因此更适合吞吐优先的批处理，不应该直接作为默认交互式部署形态。

## 1. Gateway 与 session 管理为何成为并发瓶颈

这组结果里，`send` 阶段一直很小，通常只有几毫秒到几十毫秒；真正决定总耗时的是 `wait` 阶段。例如单实例 4 会话并发的平均 `send` 只有 `8.5ms`，但平均 `wait` 是 `15.7s`；单容器 4 实例并行的平均 `send` 只有 `4.6ms`，但平均 `wait` 是 `14.5s`。这说明客户端把请求送到 Gateway 不是主要问题，主要压力在 Gateway 接收请求之后的 agent 执行、session 调度、状态维护和 vLLM 后端等待。

多会话并发会让多个 session 同时经过同一个 Gateway event loop、同一套 session store、同一套 history 读写路径和同一个 agent wait 机制。每个请求本身还会带来上下文读取、消息追加、历史加载、模型调用和结果回写。并发越高，这些共享路径越容易出现排队、锁竞争、I/O 抖动和上下文膨胀。

`history` 长尾是一个明显信号。单实例串行的 `history_p99` 只有 `17.3ms`，单实例 4 会话并发仍只有 `33.9ms`；但单容器 4 实例并行的 `history_p99` 到了 `4289.6ms`，4 容器单实例并行到了 `4425.8ms`。在 `25x2ix2w-300`、`multi-25x1dx4ix1w-500`、`multi-25x2dx2ix1w-500` 等组合里，`history_p99` 也在约 `3.8s-4.4s`。这说明当实例和容器维度增加后，session history 读取、状态目录写入和结果回收路径会变成尾延的重要来源。

因此，OpenClaw/Hermes 的瓶颈不是单点的“模型慢”或“Gateway 慢”，而是多层共享状态叠加后的排队系统：Gateway 负责接入和协调，session 管理负责状态一致性，agent wait 负责请求生命周期，vLLM 负责真正的生成。只增加并发会提高重叠度，但也会把等待和长尾集中到 `wait_p99`、`history_p99` 和 `total_p99` 上。

## 2. 不同部署模型对吞吐、延迟、尾延和资源利用率的影响

单实例串行是最低风险基线。它的 `total_mean` 和 `P95` 最低，CPU 约 `15%`，RSS 约 `0.58 GiB`，NPU AICore 约 `28.4%`。缺点是 `request_window` 达到 `1071.6s`，整批 100 个请求几乎被串行拉长，不适合吞吐目标。

单实例 4 会话并发是吞吐/资源比最好的默认候选。它把 `request_window` 从 `1071.6s` 压到 `466.8s`，`overall_output_tps` 从 `18.7` 提升到 `30.9`，NPU utilization 从 `79.9%` 提升到 `87.4%`，AICore 从 `28.4%` 提升到 `44.4%`。代价是 `total_mean` 从 `10.7s` 升到 `15.8s`，`P99` 从 `28.1s` 升到 `40.6s`。也就是说，它用更高单请求等待换来了更短整批完成时间。

单容器 4 实例并行不是好的默认扩展方式。它的 `request_window` 为 `557.2s`，比单实例 4 会话并发更慢；`P95/P99` 达到 `34.3s / 47.1s`，尾延最差；RSS 增至约 `2.0 GiB`。这说明多个 OpenClaw/Hermes 实例共享同一个容器边界时，虽然实例数增加了，但状态目录、进程调度、容器资源、Gateway 端口和后端 vLLM 入口仍然会形成竞争，收益不稳定。

4 容器单实例并行是更干净的横向隔离方式。它的 `request_window` 为 `406.9s`，`total_mean` 为 `11.4s`，`P99` 为 `24.1s`，比单容器 4 实例并行更稳，也比单实例 4 会话并发更低尾延。代价是资源开销最大：CPU 约 `57%`，RSS 约 `2.2 GiB`，磁盘写入约 `8.8 MiB/s`。它适合吞吐和隔离优先的服务，但要给宿主机资源、日志和状态写入留出余量。

`2 containers x 2 instances x 1 worker` 是吞吐更激进的方案。在 `500ms stagger` 下，`request_window` 为 `338.2s`，`P95/P99` 为 `15.5s / 27.2s`，表现好于 4 容器单实例并行；但 CPU 约 `76.8%`，RSS 约 `2.1 GiB`，说明它已经明显吃掉宿主侧资源。这个形态可以作为吞吐压测上限或批处理方案，但不适合作为没有限流和监控的线上默认值。

## 3. 为什么分层编排比单纯增加实例更重要

OpenClaw/Hermes 的扩展层次至少有四层：Host、Container、Instance、Worker。每一层解决的问题不同，不能用“增加实例数”替代。

Host 层决定 vLLM、NPU、CPU、内存、磁盘和网络的全局预算。Ascend 910C 上，vLLM 的 HBM 已经长期在 `94%-97%`，说明模型服务本身很接近显存常驻状态。OpenClaw/Hermes 侧继续加实例不会增加 HBM 容量，只会增加 CPU、内存、文件 I/O、session 状态和模型请求排队。

Container 层提供隔离边界。4 容器单实例并行虽然资源更重，但尾延明显比单容器 4 实例并行好，说明容器隔离可以减少进程、状态目录和 Gateway 运行时之间的相互干扰。相比之下，在一个容器内堆多个实例，实例数看似增加，但实际仍共享容器内运行环境和宿主调度压力，容易出现 history 长尾。

Instance 层负责 OpenClaw/Hermes 进程级并行。它可以提升并发接入能力，但也会复制 session/history/agent runtime 的状态开销。run5 里单容器 4 实例并行的 RSS 和尾延都明显恶化，说明 instance 数量不是越多越好。

Worker 层才是最细粒度的并发旋钮。单实例 4 会话并发用相对低的 RSS 和 CPU 换来了最好的吞吐/资源比，说明先调整 worker/session 并发和 stagger，通常比直接增加 instance 更有效。Worker 太少会让 NPU 和 vLLM 吃不满；Worker 太多会让 Gateway、session 和 vLLM 队列长尾变差。

所以推荐的扩展顺序是：先调 Worker 并发和 stagger，再横向增加 Container，最后才考虑增加单容器内 Instance。这样可以把并发压力分散到明确的隔离边界上，而不是把所有竞争都压在同一个 Gateway/session 运行时里。

## 4. Ascend 910C + 同机 vLLM 的推荐部署实践

### Host

在 Ascend 910C 上，vLLM 建议与 OpenClaw/Hermes 部署在同一台服务器，OpenClaw/Hermes 的 provider 指向本机 OpenAI-compatible endpoint，例如 `http://127.0.0.1:18000/v1`。这样可以避免跨机网络抖动和公网暴露，并把 NPU、vLLM、Gateway、容器资源放在同一套观测体系里。

Host 层必须持续观察 `vllm` 请求队列、NPU utilization、AICore、HBM、CPU、RSS、context switch 和磁盘写入。run5 中 HBM 基本在 `94%-97%`，AICore 在并发下从约 `28.4%` 提升到 `37.9%-44.4%`，说明 OpenClaw/Hermes 并发调度的目标不是继续吃 HBM，而是提高 vLLM 后端的有效请求重叠，同时控制尾延。

### Container

默认采用多个容器做横向隔离，而不是在一个容器里放太多 OpenClaw/Hermes 实例。每个容器应有独立状态目录、独立 gateway 端口、独立日志路径，并设置 CPU、memory、pids、nofile、shm 等限制。这样能把某个容器里的 session/history 抖动限制在局部，避免一个运行时把全局尾延拖高。

推荐从 `2-4` 个容器开始。交互式服务优先 `2` 个容器，批处理或 benchmark 可以扩到 `4` 个容器。4 容器单实例并行在 run5 中把 `request_window` 压到 `406.9s`，但 CPU、RSS 和磁盘写入都明显增加，因此容器数增加必须配合资源配额和监控阈值。

### Instance

每个容器默认运行 `1` 个 OpenClaw/Hermes 实例。只有在明确看到单实例 Gateway 接入成为瓶颈、并且 `history_p99` 与 `wait_p99` 没有恶化时，才在单容器内增加实例数。

不建议把“单容器 4 实例”作为默认。run5 中它的 `request_window` 比单实例 4 会话并发更差，`P95/P99` 明显更高，RSS 也显著上升。这说明单容器内多实例会复制运行时开销，但不一定带来更好的整体吞吐。

### Worker

Worker/session 并发是首选调参入口。默认建议每实例 `2-4` 个 worker/session，并使用 `300-500ms` 的 stagger。交互式场景优先 `1-2` 个 worker，降低排队和尾延；批处理或吞吐压测可以使用 `4` 个 worker，并通过 stagger 避免所有请求同时撞向 Gateway 和 vLLM。

如果采用单实例多会话，run5 里 `4 workers + 500ms stagger` 的吞吐/资源比很好：`request_window 466.8s`，`overall_output_tps 30.9`，CPU 约 `28.9%`，RSS 约 `0.72 GiB`。如果采用 `2 containers x 2 instances x 1 worker`，可以得到更短的 `request_window 338.2s`，但 CPU 和 RSS 明显更高，应作为吞吐优先配置，并加上限流。

### 推荐默认组合

交互式默认：

- Host：Ascend 910C 同机 vLLM，OpenClaw/Hermes 走 `127.0.0.1:18000/v1`。
- Container：`2` 个容器，每个容器独立状态目录和 gateway 端口。
- Instance：每容器 `1` 个 OpenClaw/Hermes 实例。
- Worker：每实例 `1-2` 个 worker/session，`300-500ms` stagger。
- 目标：优先压低 `total_p95/p99` 和 `history_p99`，接受较低吞吐。

批处理/吞吐默认：

- Host：同机 vLLM，并开启 vLLM、NPU、系统 CPU/RSS/磁盘统一采集。
- Container：`2-4` 个容器。
- Instance：每容器 `1` 个实例作为起点；需要更高吞吐时再测试每容器 `2` 个实例。
- Worker：每实例 `2-4` 个 worker/session，`300-500ms` stagger。
- 目标：优先缩短 `request_window`，同时设置 `wait_p99`、`history_p99`、RSS 和 CPU 的准入线。

不建议的默认组合：

- 单实例串行作为吞吐服务默认：资源低但整批完成太慢。
- 单容器 4 实例作为扩容默认：状态和 history 长尾明显放大。
- 无 stagger 的高并发突发：容易把 Gateway、session store 和 vLLM 队列同时打满。
- 只看 NPU utilization 不看 Gateway/session 指标：NPU 看似繁忙时，用户侧尾延可能已经恶化。

## 关键指标表

### 代表性部署模型

| 模型 | request_window | total_mean | total_p95 | total_p99 | output_tps | CPU | RSS | 结论 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 单实例串行 | 1071.6s | 10.7s | 11.6s | 28.1s | 18.7 | 15.0% | 0.58 GiB | 单请求稳定，吞吐最差 |
| 单实例4会话并发 | 466.8s | 15.8s | 19.2s | 40.6s | 30.9 | 28.9% | 0.72 GiB | 吞吐/资源比最好 |
| 单容器4实例并行 | 557.2s | 14.6s | 34.3s | 47.1s | 25.2 | 47.8% | 1.92 GiB | 尾延和 RSS 放大，不宜默认 |
| 4容器单实例并行 | 406.9s | 11.4s | 21.4s | 24.1s | 26.5 | 57.1% | 2.17 GiB | 隔离更好，但资源更重 |

### 更激进的多层组合

| 模型 | request_window | total_mean | total_p95 | total_p99 | CPU | RSS | 结论 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 单实例4会话并发, 500ms | 466.8s | 15.8s | 19.2s | 40.6s | 28.9% | 0.72 GiB | 资源效率高 |
| 2实例 x 2 worker, 300ms | 346.3s | 10.6s | 19.5s | 43.3s | 47.1% | 1.15 GiB | 整批更快，但 history 长尾明显 |
| 1容器 x 4实例 x 1 worker, 500ms | 557.2s | 14.6s | 34.3s | 47.1s | 47.8% | 1.92 GiB | 单容器堆实例不划算 |
| 2容器 x 2实例 x 1 worker, 500ms | 338.2s | 12.7s | 15.5s | 27.2s | 76.8% | 2.13 GiB | 吞吐强，但资源成本高 |

## 运维准入线

上线或扩大并发前，至少同时看这些指标：

- `request_window`：衡量整批吞吐。
- `total_p95` / `total_p99`：衡量用户侧尾延。
- `wait_p99`：衡量 agent/vLLM 等待长尾。
- `history_p99`：衡量 session/history 状态路径是否被放大。
- `overall_output_tps`：衡量有效生成吞吐。
- NPU utilization、AICore、HBM：衡量 vLLM 侧是否被有效利用。
- CPU、RSS、context switch、disk write：衡量 OpenClaw/Hermes 和容器层资源成本。

如果 `history_p99` 或 `wait_p99` 明显拉长，不应该继续简单增加实例数。优先降低每实例 worker、增加 stagger、拆分到独立容器，或在入口层做限流和队列控制。只有当尾延稳定、资源余量充足、vLLM 队列没有堆积时，才继续增加 Container 或 Instance。
