结论先说得直接一点：

从当前这个 `client-harness` 仓库里，我能明确确认“**不依赖模型 key**”的，只有 [`/context list`]( /root/client-harness/README.md:18 ) 这一类命令。  
`task_01` 到 `task_04` 虽然更像真实请求，但它们都是自然语言 prompt，不是显式 slash command，所以**大概率还是要走模型**，至少这个仓库里没有证据表明它们是 model-free。

这也意味着你之前本地跑 `task_05` 也出现“multi latency 更高”，反而更支持你现在的怀疑：
- 不一定是任务内容本身
- 更可能是 OpenClaw/gateway 在并发下的调度、worker queue、上下文扫描、history 处理这些公共路径出了问题

-----------------
**当前我能稳妥给你的建议**

如果目标是“更接近真实环境，但不调用模型 API”，最靠谱的不是换成 `task_01-04`，而是做这几类 model-free 压测：

- 继续用 [`/context list`](/root/client-harness/scenarios/vps/vps_docker_single.json:19)，但放大更真实的运行条件  
  例如保留 `per_worker` session、增加并发、增加历史条数、连续多轮请求。这样测到的是更真实的调度成本，而不是模型成本。
- 做“长 session”版 `/context list`  
  让同一个 session 先积累很多轮 `chat.send -> agent.wait -> chat.history`，再测后续请求。这样能更接近真实用户长期使用后的状态。
- 做“shared session”版 `/context list`  
  这个比 `per_worker` 更容易暴露同一会话上的串行化、锁竞争、去重等待、history 膨胀问题。
- 做“高 history_limit”版  
  因为 `chat.history` 本身就在你的 latency phase 里，history 越大，越能看出是不是 session/history 管理在拖慢系统。

**为什么我不推荐直接拿 task_01-04 当无模型基准**

因为这些文件虽然内容很适合真实交互：
- [task_01_openclaw_comprehension.md](/root/client-harness/tasks/task_01_openclaw_comprehension.md)
- [task_02_skill_discovery.md](/root/client-harness/tasks/task_02_skill_discovery.md)
- [task_03_local_summary.md](/root/client-harness/tasks/task_03_local_summary.md)
- [task_04_workflow_planning.md](/root/client-harness/tasks/task_04_workflow_planning.md)

但它们本质是“请回答”“请总结”“请给建议”这种自然语言任务。  
如果 backend 没有专门把它们路由到本地命令实现，那就还是模型任务。

**如果你想要真正更真实、又绝对不打模型 API**

最好的办法是新增几个明确的 model-free slash command。比如：

- `/context list --verbose`
- `/context stats`
- `/skill list`
- `/session summary`
- `/history head 20`
- `/workspace inventory`

这类命令的好处是：
- 更像真实 agent 工作流
- 会走 gateway、session、history、context、文件扫描这些公共路径
- 但不需要模型生成

这会比 `task_05` 更适合拿来单独验证“是不是调度问题”。

一句话总结：
- 现在**已确认 model-free 的只有 `/context list`**
- `task_01-04` 不能安全地当成无模型基准
- 你看到 `task_05` 和 `/context list` 都是 multi 更慢，已经很像是**调度/并发路径问题**
- 如果要继续严谨验证，下一步最好做 **更多 model-free command 型 benchmark**，而不是更多自然语言 task

如果你愿意，我可以直接帮你把现有场景再扩成 3 个无模型基准：
1. `context_list_long_session`
2. `context_list_shared_session`
3. `context_list_high_history`


--------------


看了，按你这次最新一对结果来比：

- single: `20260325T154610Z_vps-docker-single-task-00-500-full`
- multi: `20260325T154243Z_vps-docker-multi-task-00-500-10x50`

结论很清楚了：

不是 `clone/sched_yield` 这类线程创建/主动让步问题，主要还是 `futex`，而且 `openat/statx/newfstatat` 说明这条 `/context list` 路径本身确实非常 FS-heavy。

你这轮的关键数字：

- `openat`
  - single: `144894`
  - multi: `143016`
- `statx`
  - single: `630177`
  - multi: `603144`
- `newfstatat`
  - single: `33275`
  - multi: `33190`
- `clone`
  - single: `12`
  - multi: `11`
- `sched_yield`
  - single: `2`
  - multi: `1`
- `futex`
  - single: `106358`
  - multi: `120360`

怎么解读：

1. `openat/statx/newfstatat` 都非常高  
这说明 `/context list` 的确在做大量文件打开/元数据检查，不是我之前只靠 perf 栈做的推测了，现在 syscall 级别也坐实了。

2. 但这些 FS syscall 在 single 和 multi 之间总量差不大  
因为两边总请求数都是 500，所以这很像“每个请求都要做差不多的文件扫描/状态检查”。  
也就是说：
- `multi` 变慢，不是因为它突然多做了很多额外文件扫描
- 而是同样这批 FS 工作在并发下更容易互相挤

3. `clone/sched_yield` 基本可以排除  
数量极小，说明不是线程疯狂创建，也不是大量靠 `sched_yield` 在让出 CPU。

4. 真正最突出的还是 `futex`  
`multi` 的 `futex` 次数明显更高，而 `wait_mean_ms` 也显著更高：
- single `wait_mean_ms ≈ 308ms`
- multi `wait_mean_ms ≈ 2766ms`

所以现在可以把根因说得更具体：

- `/context list` 本身就是一个“高频文件元数据检查 + 一部分文本读取”的请求
- 这些 FS 操作走的是 Node/libuv 的 worker 路径
- 在 multi 并发下，真正放大的不是 `openat/statx` 本身的单次成本，而是这些 FS 任务提交、完成、回传到主线程时的同步等待
- 这个等待主要表现成 `futex`

再结合前面抓到的 perf 栈：

- `futex_wake -> uv_fs_lstat -> node::fs::LStat`
- `uv_fs_read -> node::fs::ReadFileUtf8`
- `uv__work_done -> uv__io_poll -> uv_run`

现在比较稳的结论就是：

`multi` 单请求更慢，是“同样一套文件扫描/读取工作”在并发下经过 libuv worker 队列和主事件循环同步后，被 futex 等待放大了。  
所以卡点是：
- 文件系统元数据检查很多
- 但真正拉高单请求 latency 的，是这些 FS 工作背后的同步排队/唤醒链路

一句话压缩：
不是“多线程创建太多”，也不是“md 文档锁”，而是“FS-heavy 的 `/context list` 请求在并发下引发更多 libuv/事件循环同步等待”。

如果你愿意，我下一步可以继续帮你做两件很实用的事之一：

1. 把这批最新结果重新导出成 pair report，把这些新 syscall 也放进 markdown 表里。
2. 继续深挖 `/context list` 为什么会打出这么多 `statx/openat`，直接去 OpenClaw 主代码里找是谁在扫目录/做 `lstat`。



`FS` 是 `filesystem`，也就是文件系统。这里具体指文件/目录相关操作，比如：
- `openat`: 打开文件或目录
- `statx` / `newfstatat`: 查文件元数据
- `pread64` / `read`: 读文件内容

我已经把最新这批结果重新导出了，新的 pair report 在：
- [summary.md](/root/client-harness/res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/summary.md)

而且现在 markdown 里已经有新增的：
- `**strace Key Syscalls Table**`

对应导出代码也已经改好，后面你每次跑 [export_pair_report.py](/root/client-harness/scripts/export_pair_report.py) 都会自动带这张表。

这批最新结果里，最关键的数字是：

- single:
  - `openat_count = 144894`
  - `statx_count = 630177`
  - `newfstatat_count = 33275`
  - `futex_count = 106358`
  - `futex_total_sec = 1297.624`
- multi 10x50:
  - `openat_count = 143016`
  - `statx_count = 603144`
  - `newfstatat_count = 33190`
  - `futex_count = 120360`
  - `futex_total_sec = 1141.241`

这说明两件事：

1. `/context list` 确实非常 FS-heavy  
不是猜测了，`statx/openat/newfstatat` 都非常高，说明它一直在查文件和目录状态。

2. `multi` 更慢的主因仍然不是“多了很多文件扫描”  
因为 single 和 multi 的 `openat/statx/newfstatat` 总量差不大。真正拉开差距的还是并发下的 `futex` 等待链路，也就是这些 FS 工作进入 libuv worker 和主事件循环之后的同步排队。

为什么 `/context list` 会打这么多 `statx/openat`，现在我能给出的最稳解释是：

- 镜像里的 `Context` 文档明确说，`/context list` 会展示：
  - injected workspace files
  - skills list
  - tool list / tool schemas
  - system prompt / project context 的大小
- 同一份文档也写了，OpenClaw 每次 run 会重建 system prompt，并检查/注入一组 workspace bootstrap 文件，比如：
  - `AGENTS.md`
  - `SOUL.md`
  - `TOOLS.md`
  - `IDENTITY.md`
  - `USER.md`
  - `HEARTBEAT.md`
  - `BOOTSTRAP.md`
- 再结合你这边 `perf` 栈已经看到：
  - `uv_fs_lstat -> node::fs::LStat`
  - `uv_fs_read -> node::fs::ReadFileUtf8`
  - `uv__work_done -> uv__io_poll -> uv_run`

所以最合理的解释是：
`/context list` 不是单纯返回内存里的一个计数器，而是在运行时重新检查 workspace/context 相关文件、做元数据统计、读一部分文本，然后再拼出“context breakdown”。

至于“别的 prompt/别的任务会不会也这样”，我会分三类看：

- 会有类似但通常更轻的：
  - 普通 prompt / 普通 agent 任务
  - 因为每次 run 也要重建 system prompt，也会碰到 bootstrap files 和上下文注入
- 很可能更像 `/context list` 的：
  - `/context detail`
  - `/status`
  - 任何显式要求检查 context / workspace 注入情况的命令
- 可能比 `/context list` 还重的：
  - 需要大范围读仓库文件、目录扫描、技能发现、代码搜索的任务
  - 比如你之前的 `task_05` 不是这个类型，它更偏网页读取；但如果是“总结仓库”“找某个模块”“列出技能/工具/上下文来源”，就很可能也会打出类似甚至更多的 FS syscall

所以可以把它概括成：

- `/context list` 的慢，不是因为某个 md 文件锁了
- 而是因为它本身就在做“上下文构建 + workspace 文件检查 + 文件读取”
- 普通任务也有一部分同类成本，但通常没有这么集中
- 凡是“看上下文/看仓库/扫文件”的 prompt，都更容易出现类似的 FS-heavy 特征

如果你愿意，我下一步可以继续帮你做其中一个：
1. 把这份报告再补一张“strace key syscalls”柱状图，不只是表。
2. 继续从镜像 bundle 里把 `/context list` 对应的构建产物逻辑再抠深一点，尽量定位它具体在扫哪些路径。


---
可以。先把 `agent.wait` 里“已经追到的”和“还没追到的”分开看，会比较清楚。

**已经追到的**
这些你现在已经能拿来对比了：

- 进程级资源
  - `pidstat`: `cpu_percent`, `rss_kib`, `kb_wr_per_s`, `cswch_per_s`
- 容器级资源
  - `docker_stats`: `cpu`, `mem`, `block_write`
- 磁盘级资源
  - `iostat`: `pct_util`, `w_await`, `aqu_sz`, `wkb_s`
- 主机级调度
  - `vmstat`: `interrupts`, `context switches`, `run queue`
- syscall 级
  - `strace`: `futex/openat/statx/newfstatat/read/write/...`
- 内核/用户态热点
  - `perf stat`, `perf record`

这些基本覆盖了：
- CPU 忙不忙
- 磁盘忙不忙
- syscall 在干什么
- 有没有大量同步等待
- 热点大概落在哪条调用链

**还没追到的**
`agent.wait` 里还有几块现在没有被单独切出来：

- Gateway 内部队列时间
  - 请求进入后，在真正开始执行前排了多久
- 应用层阶段拆分
  - `/context list` 内部到底是“扫目录”、“读文件”、“拼 context 文本”、“序列化响应”各花了多少
- libuv worker 队列深度
  - FS 任务提交了多少、排队多久、完成回传多久
- V8/Node 运行时细分
  - JS 执行时间
  - microtask 时间
  - GC 时间
  - event loop idle/poll 时间
- 应用层缓存命中情况
  - context 信息是不是每次都全量重建
  - 有没有目录/文件元数据缓存
- 路径级文件访问分布
  - 具体在扫哪些目录、哪些文件最热
- 业务态状态机
  - run 是 pending/running/completed 哪一段最久

如果换成真实模型任务，还额外缺：
- 模型/provider 网络往返
- provider 排队
- 推理时间
- token 生成时间

但你当前 `/context list` 这个场景里，这块基本不 relevant。

**所以现在最可能的情况**
`multi` 慢的时间，有一部分已经被 `strace/perf` 间接看到了：
- 大量 `statx/openat`
- 大量 `futex`
- `uv_fs_lstat / ReadFileUtf8 / uv__work_done`

但还有一部分不在当前追踪范围里，尤其是：
- 应用层队列等待
- libuv worker queue 排队
- JS 层把 FS 结果组装成 `/context list` 响应的时间

这也是为什么：
- syscall 总账标准化后差距没那么夸张
- 但单请求 `wait latency` 差很多

**最值得继续对比的下一层**
如果你想把 `agent.wait` 再拆开，优先级我建议是：

1. 应用层阶段日志
   - `/context list` 内部加 timing：
   - `enumerate workspace`
   - `stat files`
   - `read files`
   - `build context report`
   - `serialize/send response`

2. libuv / Node runtime 指标
   - event loop lag
   - worker queue depth / active fs jobs
   - GC 时间

3. 路径级 FS 访问画像
   - 哪些目录/文件被最频繁 `stat/open/read`

一句话：
现在 `agent.wait` 里最没被追到、但最可能解释 multi 变慢的，是“应用层排队 + libuv worker 排队 + JS 组装响应”这三段。

如果你愿意，我下一步可以直接帮你设计一版最小埋点方案，把 `/context list` 内部分成 4 到 6 个子阶段。
---
可以，先把这两层细化成“我们具体要采什么、怎么判断、能回答什么问题”。

**libuv / Node Runtime**
这一层的目标是把 `agent.wait` 里“不是 syscall 本身，而是运行时调度/排队”的部分拆出来。

建议重点采这几类：

- `event loop lag`
  - 含义：主事件循环有没有被长时间卡住，导致回调迟迟得不到执行
  - 价值：区分“FS worker 做完了，但主线程没空处理结果”这种情况
  - 关键指标：
    - `loop_lag_mean_ms`
    - `loop_lag_p95_ms`
    - `loop_lag_max_ms`

- `event loop utilization`
  - 含义：事件循环到底是忙着跑 JS/callback，还是大部分时间在等
  - 价值：判断瓶颈更偏 JS 主线程还是外部等待
  - 关键指标：
    - busy ratio
    - idle ratio

- `libuv worker pool active jobs`
  - 含义：线程池里同时有多少 FS/job 在跑
  - 价值：判断是不是 worker pool 被打满
  - 关键指标：
    - `fs_jobs_active`
    - `fs_jobs_completed_per_s`

- `libuv worker queue delay`
  - 含义：任务从提交到真正开始执行前，在队列里等了多久
  - 价值：这是最接近你现在怀疑的“multi 慢但 syscall 本身没慢多少”的核心指标
  - 关键指标：
    - `fs_queue_wait_mean_ms`
    - `fs_queue_wait_p95_ms`
    - `fs_exec_mean_ms`

- `microtask / callback pressure`
  - 含义：Promise/microtask/callback 回调是不是在堆积
  - 价值：区分“FS 已经完成，但 JS 层在慢慢消费结果”
  - 关键指标：
    - 每秒 callback 数
    - 每秒 resolved FS callback 数
    - optional: microtask checkpoint time

- `GC`
  - 含义：垃圾回收是不是插进来拉长关键路径
  - 价值：排除或确认 V8 内存压力
  - 关键指标：
    - `gc_count`
    - `gc_total_ms`
    - `gc_pause_max_ms`

- `worker threads / background threads`
  - 含义：是不是有额外 Node worker_threads 或内部线程参与
  - 价值：帮助解释 `futex` 和消息反序列化
  - 关键指标：
    - worker thread count
    - message deserialize time
    - background task count

这层最想回答的问题是：
- `multi` 慢，是慢在 `worker queue wait`，还是慢在 `event loop lag`，还是慢在 `JS callback/microtask`？

**路径级 FS 访问画像**
这一层的目标是搞清楚“到底在扫哪些路径”，而不是只知道 `statx/openat` 很多。

建议分 3 档：

- `path top-N by syscall count`
  - 哪些路径最常被 `stat/open/read`
  - 关键指标：
    - `top_statx_paths`
    - `top_openat_paths`
    - `top_read_paths`

- `path top-N by total time`
  - 哪些路径虽然次数不最多，但总耗时最高
  - 关键指标：
    - `top_paths_by_total_stat_time`
    - `top_paths_by_total_read_time`

- `path grouped by category`
  - 不一定只看单文件，更要看目录类别
  - 建议按这些分组：
    - workspace bootstrap files
    - skills
    - tool schemas
    - docs / markdown
    - config
    - node_modules / dist
    - git / hidden metadata
  - 关键指标：
    - 每类的 `count`
    - 每类的 `total_sec`
    - 每类的 `unique_paths`

如果能拿到 syscall 参数，最好额外记录：

- `unique path count`
  - 是反复扫少量热点文件，还是每次扫大量不同文件

- `miss / not found ratio`
  - 很多 `lstat` 可能是在查默认文件是否存在
  - 比如 `AGENTS.md`, `TOOLS.md`, `BOOTSTRAP.md` 这种

- `repeated metadata checks`
  - 同一路径被短时间内反复 `stat`
  - 这对判断“能不能缓存”特别关键

这层最想回答的问题是：
- `/context list` 是在反复查固定那几份 bootstrap/context 文件？
- 还是在扫描整个 workspace？
- 还是在扫 skills / tool schema / docs 目录？
- 哪些路径最值得缓存或预计算？

**我会怎么落地**
如果我们后面真的做埋点，我建议：

1. 运行时指标
   - 在 gateway 里加轻量应用层 timing
   - 单独记 `fs_queue_wait`, `fs_exec`, `callback_process`, `report_build`

2. 路径级画像
   - `strace` 侧补 `-yy` 或更丰富输出
   - 或直接在 Node FS 包装层记录 path + op + duration
   - 应用层记录通常比 raw strace 更容易汇总

3. 报表输出
   - `runtime_metrics` 表
   - `fs_path_hotspots` 表
   - `fs_category_breakdown` 表
   - 再配两张图：
     - `fs_queue_wait timeline`
     - `top path categories bar chart`

**一句话总结**
- `libuv / Node runtime` 这一层，是要找“排队和调度”
- `路径级 FS 访问画像` 这一层，是要找“到底在扫什么”
- 这两层一起补上，基本就能把 `agent.wait` 里现在最模糊的部分拆开

如果你愿意，我下一步可以直接给你出一版最小实现方案：
- 哪些指标在 OpenClaw 里加埋点
- 哪些还能继续用 `strace/perf`
- 最后怎么接到 `summary.json` 和 `export_pair_report` 里
---

已经开始做了，而且最新 report 里已经有这层结果：

- 新图： [runtime_category_pct.png](/root/client-harness/res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/figures/runtime_category_pct.png)
- 新表： [summary.md](/root/client-harness/res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/summary.md) 里的
  - `Runtime Category Samples Table`
  - `Runtime Category Percent Table`

目前这版 runtime 分类是基于 `perf record` 的 CPU 栈样本，把样本分到：
- `fs_worker_exec`
- `event_loop_poll`
- `microtask`
- `futex_sync`
- `worker_message`
- `libuv_worker_other`
- `gateway_main_other`
- `v8_worker`

**先说当前结论**
就你这批最新结果来看：

- `multi` 变慢，不像是 `event loop lag` 主导
  - `event_loop_poll`
    - single: `9.668%`
    - multi: `7.805%`
  - 如果是 event loop 更卡、更长时间陷在 poll/lag，通常这里不会更低

- 也不像是“FS worker 实际执行时间”主导
  - `fs_worker_exec`
    - single: `0.108%`
    - multi: `0.136%`
  - 差异很小，而且占比很低

- 目前更像是“JS callback / microtask 处理链路”更重
  - `microtask`
    - single: `71.999%`
    - multi: `72.938%`
  - `gateway_main_other`
    - single: `11.102%`
    - multi: `11.941%`
  - `libuv_worker_other`
    - single: `1.371%`
    - multi: `1.556%`

所以在你问的三个方向里，基于当前数据，我会这样判断：

- `event loop lag`: 目前不像主因
- `worker queue wait`: 现在还不能直接确认
- `JS callback / microtask`: 目前最像

**为什么还不能直接确认 worker queue wait**
因为我们现在这层 runtime 分类用的是 `perf record` 的 `cpu-clock` 采样。

这意味着它更擅长看到：
- 哪些代码正在占 CPU
- 栈上在跑什么函数

但不擅长直接看到：
- 任务在 libuv 队列里“纯等待”了多久

也就是说：
- 如果 `worker queue wait` 是“排队但没占 CPU”的时间
- 那它不会在 `cpu-clock` 样本里很明显地冒出来

这也是为什么你会看到：
- `fs_worker_exec` 占比不高
- 但请求还是很慢

这不矛盾，反而说明：
- 真正的慢，有可能就是“执行前排队”
- 以及“执行完之后 JS callback/microtask 消化结果”的时间

**把现在的判断压缩成一句话**
这批新数据更支持：
- `multi` 慢，主要不是慢在 event loop poll
- 也不是慢在 FS worker 真正在干活
- 更像慢在 `FS 任务完成后` 的 JS callback/microtask 处理，以及一部分当前 `perf cpu-clock` 看不见的队列等待

**这次已经落地的内容**
我已经把这层分析接进代码了：
- [parsers.py](/root/client-harness/src/openclaw_harness/parsers.py) 现在会给 `perf_record.summary.json` 生成 `runtime_samples`
- [export_pair_report.py](/root/client-harness/scripts/export_pair_report.py) 会把 runtime category 表和图一起导出

**下一步最值得做的**
如果你想把 `worker queue wait` 直接坐实，而不是继续靠推断，我建议下一步做其中一个：

1. 应用层埋点
   - 在 OpenClaw `/context list` 实现里记录：
   - FS 任务提交时间
   - FS 任务开始执行时间
   - FS 完成回调时间
   - report 拼装完成时间

2. Node runtime 诊断日志
   - event loop delay
   - active fs jobs
   - pending fs jobs
   - callback drain time

现在这一步，我们已经把结论推进到：
`multi` 更像慢在 callback/microtask + 队列等待，而不是 event loop poll 或 FS worker 真正在跑。
---
这轮新结果已经把结论坐实很多了。最新对比在 [summary.md](/root/client-harness/res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/summary.md)，原始 Node trace 在 [single node_trace.summary.json](/root/client-harness/out/20260325T173324Z_vps-docker-single-task-00-500-full/node_trace.summary.json) 和 [multi node_trace.summary.json](/root/client-harness/out/20260325T174736Z_vps-docker-multi-task-00-500-10x50/node_trace.summary.json)。

结论先说：
- `multi` 主要更像卡在 `FS async queue wait / 共享调度队列等待`。
- 不是 `event loop` 主导。
- 也不像 `callback/microtask` 主导。
- 有共享状态/共享同步点竞争的迹象，但更像 runtime/session 队列与锁文件相关的串行化，不像某个业务逻辑大锁单独把 10 秒都吃掉。

最关键的证据有 4 条。

1. `wait` 暴涨，但 CPU/磁盘几乎没变  
- single `wait_mean = 973.591 ms`
- multi `wait_mean = 10082.269 ms`

但同时：
- 进程 CPU：`44.01%` vs `43.09%`
- 磁盘 `pct_util`: `0.374` vs `0.380`
- 磁盘 `w_await`: `1.201 ms` vs `1.311 ms`

所以不是磁盘堵住了，也不是 CPU 被打满了。

2. syscall 工作量几乎一样，说明不是“multi 做了更多活”  
`statx/openat/newfstatat` 两边几乎一模一样：
- `statx`: `798797` vs `800835`
- `openat`: `159096` vs `159416`
- `newfstatat`: `33660` vs `33624`

而且 syscall 平均耗时也几乎一样：
- `statx_mean_ms`: 两边都是 `0.022`
- `openat_mean_ms`: 两边都是 `0.028`

这说明内核里真正做文件操作的时间没变，变慢发生在 syscall 之外。

3. Node trace 直接指向 `fs_async` 这层，而不是 callback / event loop  
这是这轮最重要的新证据：

- `fs_async_mean_ms`
  - single: `143.511`
  - multi: `201.681`
- `fs_callback_mean_ms`
  - single: `163.739`
  - multi: `158.562`
- `promise_callback_mean_ms`
  - single: `2.741`
  - multi: `2.781`
- `event_loop_immediate_mean_ms`
  - single: `1.546`
  - multi: `2.366`

这里最有区分度的是：
- `fs_async` 明显变慢了
- `fs_callback` 没变慢，反而略低
- `promise_callback` 基本没变
- `event_loop_immediate` 有一点上升，但量级远不够解释 `wait` 从 1 秒到 10 秒

所以三选一的话，这轮我会明确判：
- 第一主因：`queue wait`
- 第二：少量 event loop / immediate 放大
- 第三：`callback/microtask` 不是主因

4. 共享状态竞争确实存在，而且能看到热点  
`futex` 还是高度集中在少数地址上：
- single top6 占 `75.02%`
- multi top6 占 `77.03%`

这说明不是随机等待，而是少数共享同步点反复 wake/wait。

再结合路径热点：
- 两边最热路径都是 `sessions.json.lock`
- single 这条路径总耗时 `298.634 ms`
- multi 变成 `733.853 ms`
- multi 里 `/home/node/.openclaw/agents/main/sessions` 目录本身也升到了 `1781.805 ms`

这说明并发下，`session` 相关状态和锁文件访问确实更重了。

但我不会说“根因就是这个 lock 文件”，因为它的总耗时还不够解释整整 9 秒差距。更准确的说法是：
- 有共享状态竞争
- 其中 session/state 目录和 lock 文件是可见热点
- 但更大的主因仍然是大量 FS async 工作在共享队列里排队

一句话总结：
`multi` 慢，主要不是慢在磁盘、event loop、或 JS callback，本质上更像 `/context list` 这条 FS-heavy 路径在并发下进入了共享的 FS async/调度队列，外加少数 session/synchronization 热点，把 `agent.wait` 拉长了。

如果你愿意，我下一步可以继续做两件最值钱的事之一：
- 把 `embedded_run_span` 那些阶段日志也解析进 summary，直接算出 `bootstrap_load / skills / context_bundle / reply_dispatch queue` 各阶段 single vs multi 的时间。
- 专门把 `sessions.json.lock`、`sessions/`、bootstrap 文件这几类路径单独出一张对比表，看看哪一类增长最明显。

---

已经继续拆了，最新报告里现在能单独看到：

- `sessions.json.lock`
- `sessions.json`
- `sessions.json.<uuid>.tmp`
- `sessions/` 目录本身的枚举/解析
- `bootstrap files`

表在 [summary.md](/root/client-harness/res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/summary.md#L115)，timeline 图在 [node_focus_timeline.png](/root/client-harness/res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/figures/node_focus_timeline.png)。这次我还把 `sessions_tmp` 接进了导出链路，代码在 [parsers.py](/root/client-harness/src/openclaw_harness/parsers.py) 和 [export_pair_report.py](/root/client-harness/scripts/export_pair_report.py)。

从最新结果看，确实存在你说的那条 session 操作链，而且证据很强：

- 查找 / 解析 session 目录：有大量 `realpath` 打在 `/home/node/.openclaw/agents/main/sessions` 上。single `77.678ms`，multi `1781.805ms`，见 [summary.md](/root/client-harness/res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/summary.md#L117)。
- 判断目录/文件是否存在：大量 `lstat`，尤其打在 `sessions.json.lock` 和 `sessions.json.<uuid>.tmp` 上。
- 共享锁文件：`sessions.json.lock` 明显存在，而且 multi 更重，`298.634ms -> 733.853ms`。
- 临时文件写入链：`sessions.json.<uuid>.tmp` 很明显，single `327.700ms`，multi `1679.839ms`。从 trace 样本能看到固定模式：
  - `open tmp`
  - `chmod tmp`
  - `chmod sessions.json`
  - `lstat tmp`
  - `unlink sessions.json.lock`
  见 [node_trace.parsed.csv](/root/client-harness/out/20260325T174736Z_vps-docker-multi-task-00-500-10x50/node_trace.parsed.csv)。
- session 索引文件：`sessions.json` 也有固定访问，`164.106ms -> 210.497ms`。
- session 目录下文件：运行时目录里确实是一组 session `.jsonl` 文件加一个 `sessions.json` 索引，见 [sessions dir](/root/client-harness/out/20260325T174736Z_vps-docker-multi-task-00-500-10x50/runtime/config/agents/main/sessions) 和 [sessions.json](/root/client-harness/out/20260325T174736Z_vps-docker-multi-task-00-500-10x50/runtime/config/agents/main/sessions/sessions.json)。

所以现在更像是：

- 有 session manager 级别的共享串行化
- 至少包含 `sessions.json.lock` 这把锁
- 并发下更重的不是 `sessions.json` 本身，而是：
  - `sessions/` 目录 realpath/枚举
  - `sessions.json.<tmp>` 临时文件写入链
  - `sessions.json.lock` 锁文件访问

这很像“更新全局 session 索引时要拿共享锁，然后走 tmp 文件落盘/替换”的模式，所以“session manager 有共享锁，排队”这个判断，我现在会说：**是，高概率有，而且已经有 trace 证据支持**。  
但“读取或准备 history / transcript / metadata 文件”这一层，这批 Node trace 里还没有直接命中对应路径名；当前更明确看到的是 session 索引和 session `.jsonl` 所在目录这一层，而不是单独叫 `history/transcript/metadata` 的文件名。

额外一个很关键的对照是 [Gateway Runtime Stage Table](/root/client-harness/res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/summary.md#L108)：
- `execution_admission_wait_mean_ms`: `0.143 -> 9.253`
- `skills/context_bundle` 基本没变

所以整体结论还是：
- `multi` 慢，主因更像执行前 admission/queue wait
- 这个排队和 session manager 的共享锁 + 目录/索引更新链路高度相关

如果你要，我下一步可以继续把 `sessions.json.<uuid>.tmp` 和 `sessions.json.lock` 各自再画成单独双图，并把 session `.jsonl` 文件访问也单独归一类。
---
可以这么总结，但我会稍微说得更准确一点：

`multi` 更慢，主因很像是 **session manager 相关的共享串行化 + session 状态目录/索引文件更新链路在并发下被放大**，而不只是“单纯扫目录”。

目前证据支持这几个点：

- 有共享锁迹象  
  `sessions.json.lock` 明确存在，而且 multi 更重，见 [summary.md](/root/client-harness/res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/summary.md#L117)。
- 有全局 session 索引更新链  
  `sessions.json`、`sessions.json.<uuid>.tmp`、`sessions.json.lock` 这套路径一起出现，像典型的“拿锁 -> 写 tmp -> 更新索引 -> 释放锁”。
- `sessions/` 目录本身的解析/realpath 在 multi 下涨得最明显  
  `sessions_dir_enum_total_ms` 从 `77.678` 到 `1781.805`，涨幅非常大，见同一张表。
- `sessions_tmp_total_ms` 也明显涨  
  `327.700 -> 1679.839`
- `execution_admission_wait_mean_ms` 也从 `0.143` 到 `9.253`
  说明很多时间耗在真正执行前的 admission / scheduling wait，见 [Gateway Runtime Stage Table](/root/client-harness/res/vps-docker-single-task-00-500-full-vs-vps-docker-multi-task-00-500-10x50/summary.md#L108)。

所以一句话版本可以说成：

`multi` 更慢，主要不是模型算得慢，也不是磁盘本身慢，而是并发下 session manager 的共享状态更新被放大了：看起来有一把全局 session 索引锁，同时每个 session 都会触发 `sessions/` 目录解析、`sessions.json` 更新、临时文件写入这条链路，最终把 admission/queue wait 拉高。

我会补一个小修正：

- “每个 session 都要扫描目录建临时文档”这个说法，方向对，但更精确应该是：
  - 不是在建普通“临时文档”
  - 更像是在更新 session 索引时写 `sessions.json.<uuid>.tmp`
  - 并伴随 `sessions/` 目录 realpath / 元数据访问

所以最稳的总结是：
**高概率存在 session manager 级别的全局共享锁或等价串行化点；并发下每个 session 的索引更新、目录解析、tmp 文件写入会互相排队，这是 multi 更慢的主要原因。**

如果你愿意，我可以下一步把这段话整理成一段可以直接放进报告结论区的英文/中文摘要。

---
可以，按你现在这套报告，基本可以分成这三类。

| 类别 | 指标/文件 | 代表什么 |
| --- | --- | --- |
| `client observed` | `latency.csv`, `latency_ms.connect/send/wait/history/total` | client 视角看到的一次完整请求耗时 |
| `gateway process` | `pidstat`, `strace`, `perf_stat`, `perf_record`, `node_trace`, `gateway_runtime_spans` | gateway 进程内部在做什么、卡在哪、哪些路径慢 |
| `container / host system` | `docker_stats`, `iostat`, `vmstat` | 容器整体资源、宿主机磁盘、宿主机调度/中断等系统层状态 |

再细一点对应如下：

| 指标 | 层级 | 说明 |
| --- | --- | --- |
| `wait_mean_ms` | `client observed` | client 等待 agent 完成的时间 |
| `history_mean_ms` | `client observed` | client 拉回 history 的时间 |
| `pidstat cpu_percent/rss_kib/kb_wr_per_s/cswch_per_s` | `gateway process` | gateway 这个进程自己的 CPU/内存/写入/上下文切换 |
| `strace futex/openat/statx/...` | `gateway process` | gateway 进程触发了哪些 syscall |
| `perf context-switches/cpu-migrations/...` | `gateway process` | gateway 进程相关的 perf 指标 |
| `perf_record runtime samples` | `gateway process` | gateway CPU 栈热点，偏用户态/运行时分类 |
| `node_trace` | `gateway process` | Node/libuv/fs/runtime 事件，最接近 gateway 内部阶段 |
| `gateway_runtime_spans` | `gateway process` | gateway 应用层埋点阶段，比如 `execution_admission_wait` |
| `docker_stats cpu/mem/block_write` | `container system` | 整个 gateway 容器整体资源消耗 |
| `iostat w_await/pct_util/aqu_sz` | `host system` | 宿主机磁盘设备层状态 |
| `vmstat interrupts/context_switches/run_queue` | `host system` | 宿主机整体调度和中断状态 |

所以你现在这份结论里：

- “multi 更慢”这个现象
  - 是从 `client observed` 的 latency 看出来的
- “慢在 execution admission wait”
  - 是从 `gateway process` 的 `gateway_runtime_spans` 看出来的
- “和 sessions 目录 / lock / tmp 文件有关”
  - 也是从 `gateway process` 的 `node_trace/strace` 看出来的
- “不是磁盘打满”
  - 是从 `host system` 的 `iostat/vmstat` 看出来的

如果你愿意，我还可以把这张表直接整理进 `metrics_guide.md` 或 report 说明里。
---

是，主要就是采集变重了，不是单一原因，但“打了很多 span / trace / syscall 采集”是大头。

现在这轮比之前慢，主要叠了这几层开销：

- `strace`
  会附着到 gateway 进程，追很多 syscall。这个对高频 `futex/openat/statx/...` 路径本身就有明显开销，配置在 [scenario.py](/root/client-harness/src/openclaw_harness/scenario.py) 和 [vps_docker_multi.json](/root/client-harness/scenarios/vps/vps_docker_multi.json)。
- `perf record`
  这是持续采样，也会拖慢一点，尤其并发高时。
- `node trace`
  现在还开了 `node.async_hooks/node.fs/node.environment` 这些 trace category，会让 Node 运行时额外写大量 trace event，见 [runtime.py](/root/client-harness/src/openclaw_harness/runtime.py)。
- collector 变多了
  现在不是只有 `docker_stats/pidstat/iostat`，还同时开了 `strace + node_trace + perf_stat + perf_record`，整体就比最早那版重很多。

另外还有两个“不是采集本身，但会让整轮墙钟更长”的变化：

- 我为了把 `multi` 跑稳，加了连接限流  
  [runner.py](/root/client-harness/src/openclaw_harness/runner.py) 里现在最多 4 个 worker 同时 `connect()`。
- 我把 `worker_stagger_ms` 从 `150` 提到了 `600`  
  这会让 20 个 worker 分批连上，启动阶段本来就会更长，见 [vps_docker_multi.json](/root/client-harness/scenarios/vps/vps_docker_multi.json)。

所以更准确地说：

- 单请求变慢：主要是 tracing/profiling 开销
- 整轮墙钟更长：除了 tracing，还因为我故意把连接阶段放缓，避免 handshake timeout

如果你想要“更接近真实性能”的 benchmark，我建议分两种跑法：

- 轻量基准
  关掉 `strace`、`node_trace`、`perf_record`，只留 `docker_stats/pidstat/iostat/vmstat`
- 诊断基准
  保留现在这套重采集，用来定位瓶颈

如果你愿意，我可以直接帮你再加一个 `vps_docker_multi_light.json`，专门做低开销基准。