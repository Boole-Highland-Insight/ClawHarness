# Benchmark Metrics Guide

这个文档解释 `benchmarks/client-harness` 里几个核心 phase，以及 `out/` 目录中常见 metrics 的含义。

## 请求执行链路

当前 harness 的一次请求，核心会经过这条链路：

1. `connect`
2. `chat.send`
3. `agent.wait`
4. `chat.history`

其中真正按请求循环执行的主要是：

1. `send`
2. `wait`
3. `history`

`connect` 更像 worker 建连成本，通常不是每条请求都重新完整计算一次。

## Phase 含义

### `connect`

- 含义：客户端和 OpenClaw gateway 建立 WebSocket 连接，并完成 `connect` 握手。
- 对应代码：`client-harness/src/openclaw_harness/gateway_client.py`
- 更接近什么：客户端“接入系统”的成本。
- 什么时候重要：
  - 频繁新建连接
  - 短连接场景
  - 比较初次接入成本
- 注意：
  - `connect_latency_ms` 往往是按 worker 统计的，不一定是每条请求都重新建立连接。
  - 一般不要把它直接和 `total_latency_ms` 相加理解。

### `send`

- 含义：调用 `chat.send` 的耗时。
- 更接近什么：把一条消息成功提交给 gateway / agent 系统的成本。
- 包含的可能内容：
  - 请求进入 gateway
  - 请求校验
  - run 创建 / 调度开始
- 通常怎么解读：
  - 如果 `send` 很高，可能说明入口调度、排队、提交阶段已经有压力。

### `wait`

- 含义：调用 `agent.wait` 的耗时。
- 更接近什么：系统真正处理这条请求并产出最终结果的时间。
- 这是最关键的 phase。
- 包含的可能内容：
  - agent 执行
  - 命令处理
  - 模型推理或内部任务处理
  - 并发下的等待 / 排队
- 通常怎么解读：
  - 如果 `wait` 明显升高，说明瓶颈更可能在“请求处理本身”。
  - 并发场景下，`wait` 往往最能反映真实压力。

### `history`

- 含义：调用 `chat.history` 拉回会话历史的耗时。
- 更接近什么：结果已经生成后，读取会话结果的成本。
- 通常怎么解读：
  - 如果 `history` 高，问题更可能在会话历史读取、存储访问、返回序列化这类环节。
  - 如果 `history` 很稳定，而 `wait` 波动大，通常说明真正的问题不在 history 读取。

### `total`

- 含义：一次完整 `send -> wait -> history` 的总耗时。
- 更接近什么：单条请求的端到端完成时间。
- 注意：
  - 通常不包含 `connect`。
- 通常怎么解读：
  - 这是最适合直接做“用户体感延迟”对比的指标。

## 延迟聚合指标

`summary.json` 中每个 phase 通常会有这些聚合值：

### `count`

- 样本数。
- 例如 `total.count = 100` 表示一共统计了 100 条成功请求。

### `min`

- 最快一次请求的耗时。

### `max`

- 最慢一次请求的耗时。

### `mean`

- 平均耗时。
- 更接近整体平均体验。
- 缺点：
  - 容易被极端慢请求拉高。

### `p50`

- 50 分位数，也就是中位数。
- 更接近“典型请求”的耗时。

### `p95`

- 95 分位数。
- 表示 95% 的请求都不超过这个值。
- 适合看较差但仍常见的延迟体验。

### `p99`

- 99 分位数。
- 表示最差 1% 请求的大致水平。
- 适合看长尾延迟。

## 如何解读 `p99` 明显高于 `mean`

如果：

- `mean` 不高
- 但 `p99` 比 `mean` 高很多

通常说明：

- 大多数请求不慢
- 但有少量请求特别慢
- 系统存在明显长尾延迟

这在并发场景里通常意味着：

- 队列等待
- 共享资源竞争
- event loop 抖动
- 容器 / WSL 调度抖动
- 少量请求命中了更慢的执行路径

简单经验：

- `p99` 只比 `mean` 高一点：系统比较稳定
- `p99` 远高于 `mean`：长尾明显，需要重点关注

## `latency.csv` 里的字段

### `worker_id`

- 第几个 worker。
- 可以理解为第几个模拟客户端。

### `request_index`

- 这个 worker 发出的第几条请求。

### `session_key`

- 当前请求所属的 session。
- 如果 `session_mode=per_worker`，同一个 worker 的多次请求会复用同一个 session。

### `run_id`

- 这次请求对应的唯一运行标识。

### `success`

- 这次请求是否成功完成。

### `send_status`

- `chat.send` 返回的状态。

### `wait_status`

- `agent.wait` 返回的状态。

### `history_messages`

- 当前会话中读取到的消息数。
- 在复用 session 时，这个数字通常会增长。

### `error`

- 失败时记录的异常信息。

## `summary.json` 中的高层字段

### `requests_total`

- 总请求数。

### `requests_ok`

- 成功请求数。

### `requests_failed`

- 失败请求数。

### `latency_ms`

- 各 phase 的聚合延迟统计。

### `preflight`

- 运行前检查摘要。
- 包括：
  - 目标 URL
  - healthcheck URL
  - container / PID 信息
  - warning

### `environment`

- 当前宿主环境摘要。
- 包括：
  - 是否在 WSL
  - OS / kernel 信息
  - docker / pidstat / perf 是否可用
  - 推荐启用哪些 collectors

### `collector_analysis`

- collectors 解析后的汇总结果。
- 如果 collectors 被关闭或不可用，这里可能为空。

## Collector Metrics 含义

### `docker_stats.csv`

Docker 容器维度的资源使用情况。

常见字段：

- `cpu_percent`
  - 容器 CPU 使用率。
- `mem_percent`
  - 容器内存使用率。
- `mem_usage_limit`
  - 内存使用量 / 限制。
- `net_io`
  - 网络收发量。
- `block_io`
  - 块设备 IO。
- `pids`
  - 容器内进程数。

适合看：

- 容器是否吃满 CPU
- 内存是否增长
- 资源是否在并发下明显放大

### `pidstat`

进程维度的系统指标。

#### CPU 部分

- `%usr`
  - 用户态 CPU
- `%system`
  - 内核态 CPU
- `%guest`
  - guest CPU
- `%wait`
  - IO wait
- `%CPU`
  - 总 CPU 使用

#### Memory 部分

- `VSZ`
  - 虚拟内存大小
- `RSS`
  - 常驻内存
- `%MEM`
  - 内存占比
- `minflt/s`
  - 次缺页
- `majflt/s`
  - 主缺页

#### IO 部分

- `kB_rd/s`
  - 每秒读
- `kB_wr/s`
  - 每秒写
- `kB_ccwr/s`
  - cancelled writeback
- `iodelay`
  - IO delay

适合看：

- 哪个阶段 CPU 吃高了
- 内存是否膨胀
- IO 是否成为瓶颈

### `perf_stat`

更偏 CPU profiling 的计数器级统计。

常见信息：

- event 名称
- counter value
- runtime
- running percent
- metric value

适合看：

- CPU 指令级 / 事件级趋势
- 更正式的性能归因

在 WSL 上通常不如真实 Linux VPS 稳定。

### `perf_record`

- 主要产物是 `perf.data`
- 用于后续 flame graph / hotspot 分析
- 它本身不是一个简单的“一个数字”的汇总指标

适合看：

- 热点函数
- 调用栈
- 真正的 CPU 时间花在哪里

## Single Worker / Multi Worker 的真实含义

### Single worker

- 代表一个模拟客户端。
- 更接近“单用户 / 单会话持续请求”。

### Multi worker

- 代表多个模拟客户端并发请求。
- 更接近“多个用户 / 多个会话同时打到同一个 gateway”。

注意：

- 这里更准确的说法是“单并发 / 多并发”
- 不一定等同于传统意义上的“单线程 / 多线程”
- harness 主要通过 `asyncio` task 来并发模拟多个客户端

## 解读建议

看结果时，推荐顺序：

1. 先看 `requests_failed`
2. 再看 `total.mean / total.p95 / total.p99`
3. 然后拆开看 `send / wait / history`
4. 如果 `wait` 是主要瓶颈，再看 collectors
5. 如果 `p99` 明显大于 `mean`，优先排查长尾原因

一句话总结：

- `total` 看整体体验
- `wait` 看真正处理瓶颈
- `p95/p99` 看尾延迟
- collectors 看资源侧证据

## Collector 对照表

| 观测手段 | 观测层级 | 典型字段 | 最适合回答的问题 |
|---|---|---|---|
| `latency_ms` / `latency.csv` | 请求级 | `send_latency_ms` `wait_latency_ms` `history_latency_ms` `total_latency_ms` | 慢在哪个 phase，单 worker / 多 worker 哪个阶段被放大 |
| `docker_stats` | 容器级 | `cpu_percent_value` `mem_percent_value` `mem_usage_bytes` `net_rx_bytes` `net_tx_bytes` `block_read_bytes` `block_write_bytes` `pids_value` | 整个容器 CPU / 内存 / 网络 / block IO 是否在并发下升高 |
| `pidstat` | 进程级 | `pct_cpu` `pct_wait` `rss_kib` `pct_mem` `kb_rd_per_s` `kb_wr_per_s` `iodelay` | gateway 进程本身是不是 CPU / 内存 / IO 在忙，`wait` 升高时进程级 IO 是否也在升高 |
| `iostat` | 宿主机磁盘设备级 | `r_s` `w_s` `rkb_s` `wkb_s` `r_await` `w_await` `aqu_sz` `pct_util` | 底层磁盘是否在卡，`await` / `%util` / 队列长度是否在多 worker 下明显变高 |
| `perf_stat` | CPU 计数器级 | `counter_value` `runtime_ms` `running_pct` `metric_value` | 更正式的 CPU 计数器分析，适合 VPS 上做 CPU 瓶颈归因 |
| `perf_record` | 调用栈 / 热点级 | `perf.data` | 哪些函数真正耗 CPU，适合后续 flame graph / hotspot 分析 |

## 现在 summary.json 里能看到什么

如果你启用了 collectors，当前 `summary.json` 里的 `collector_analysis` 里会出现这些高层键：

- `collector_analysis.docker_stats`
- `collector_analysis.pidstat`
- `collector_analysis.iostat`
- 需要时还会有：
  - `collector_analysis.perf_stat`
  - `collector_analysis.perf_record`

### `collector_analysis.docker_stats`

这是容器级摘要，典型结构是：

- `container`
- `rows`
- `metrics.cpu_percent_value`
- `metrics.mem_percent_value`
- `metrics.mem_usage_bytes`
- `metrics.mem_limit_bytes`
- `metrics.net_rx_bytes`
- `metrics.net_tx_bytes`
- `metrics.block_read_bytes`
- `metrics.block_write_bytes`
- `metrics.pids_value`

每个 `metrics.*` 下都会有：

- `count`
- `min`
- `max`
- `mean`
- `p50`
- `p95`
- `p99`

### `collector_analysis.pidstat`

这是进程级摘要，典型结构是：

- `sections.cpu.metrics`
- `sections.memory.metrics`
- `sections.io.metrics`

重点字段通常包括：

- CPU
  - `pct_usr`
  - `pct_system`
  - `pct_wait`
  - `pct_cpu`
- Memory
  - `vsz_kib`
  - `rss_kib`
  - `pct_mem`
- IO
  - `kb_rd_per_s`
  - `kb_wr_per_s`
  - `kb_ccwr_per_s`
  - `iodelay`

### `collector_analysis.iostat`

这是宿主机磁盘设备级摘要，典型结构是：

- `busiest_device_by_util_mean`
- `devices.<device>.metrics`

重点字段通常包括：

- `r_s`
- `w_s`
- `rkb_s`
- `wkb_s`
- `r_await`
- `w_await`
- `aqu_sz`
- `pct_util`

这也是最适合回答下面几个问题的一层数据：

- 当前慢是不是磁盘 / overlay2 / docker 存储层在卡
- `wait` 变高时，底层磁盘是不是也在高 `await`
- 多 worker 时 `%util`、队列长度、写入速率是不是明显上升

## 实战解读顺序

当你跑 `resource_profile` 场景时，建议按下面顺序看：

1. 先看 `latency_ms.total` 和 `latency_ms.wait`
2. 再看 `collector_analysis.pidstat.sections.io`
3. 再看 `collector_analysis.docker_stats.metrics.block_write_bytes`
4. 最后看 `collector_analysis.iostat.devices.<busiest_device>.metrics`

如果你看到下面这种组合：

- `wait.mean` 升高
- `pidstat.kb_wr_per_s` 升高
- `docker_stats.block_write_bytes` 升高
- `iostat.w_await` / `aqu_sz` / `pct_util` 也升高

那就很像是：

- 底层磁盘 / overlay2 / Docker 存储写入路径在拖慢请求

如果你看到的是：

- `wait.mean` 升高
- 但 `iostat.await` 和 `%util` 都不高
- `pidstat.pct_cpu` 却明显升高

那更像是：

- CPU 或应用处理路径本身变慢
