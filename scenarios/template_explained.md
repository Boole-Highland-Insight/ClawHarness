# Scenario Template Explained

这个文件是给人看的场景模板，不是给 harness 直接解析的 scenario JSON。

## 文件定位

- `scenario` 负责“怎么跑”：运行方式、并发、采样器、时间参数。
- `task` 负责“发什么”：真正要交给模型的 prompt。
- 运行入口仍然只有 `python -m openclaw_harness run --scenario <file>`。

## 字段说明

### `name`

- 场景名称。
- 会出现在输出目录名、`summary.json` 和 `meta.json` 里。
- 建议使用短横线风格，比如 `docker-single-task-context`。

### `runtime`

这一组控制 harness 如何启动和连接 gateway。

- `kind`
  - 运行方式。
  - `docker` 表示由 harness 启动容器。
  - `host_direct` 表示直接连接宿主机上的 gateway。
- `image`
  - Docker 场景里要启动的镜像名。
  - 通常指向本地构建出来的 benchmark 镜像。
- `container_name_base`
  - 容器名的前缀。
  - harness 会在后面拼上场景名和随机后缀，避免重名。
- `instance_num`
  - 要同时启动多少个独立 runtime 实例。
  - 默认是 `1`。
  - 当它大于 `1` 时，harness 会并发运行多份相同负载，并为每个实例单独创建容器、collector 子目录和结果摘要。
  - 当前只支持新的 Docker 容器模式，不支持 `host_direct`，也不支持单个 `reuse_container_name` 复用成多实例。
- `reuse_container_name`
  - 复用已存在的 Docker 容器名。
  - 非空时，harness 不再新建或删除容器，而是直接连接这个容器里的 gateway。
  - 这种模式下，`container_port` 表示容器内 OpenClaw gateway 的监听端口。
- `host`
  - 宿主机地址。
  - harness 访问 gateway 的目标主机。
- `host_port`
  - 宿主机对外暴露的端口。
  - harness 会连这个端口发 WebSocket 请求。
  - 当 `instance_num > 1` 时，harness 会把它当作基准端口，自动为后续实例分配不冲突的端口。
  - `bridge` 网络默认按 `+1` 递增；`host` 网络会预留更大的步长，避免 browser control
    之类的辅助端口和别的实例冲突。
- `container_port`
  - 容器内部 gateway 监听的端口。
  - 当 `reuse_container_name` 非空时，harness 会用它配合 `docker inspect` 出来的容器 IP
    或 host 网络来构造连接地址。
- `gateway_bind`
  - gateway 绑定方式。
  - 控制容器内服务对外可见的监听范围。
- `gateway_token`
  - harness 和 gateway 认证用的 token。
- `build_image_if_missing`
  - 如果本地没有对应镜像，是否自动构建。
- `force_rebuild`
  - 是否无视缓存强制重建镜像。
- `skip_channels`
  - 是否跳过真实外部渠道连接，只测 gateway / client 路径。
- `startup_timeout_sec`
  - 等待 runtime 启动完成的超时时间，单位秒。
- `keep_container`
  - 测试结束后是否保留容器，便于事后排查。
- `repo_root`
  - repo 根目录路径。
  - 通常留空，由 harness 自动推断。
- `dockerfile`
  - 构建镜像时使用的 Dockerfile 路径。
  - 通常留默认值即可。

### `client`

这一组控制发给 gateway 的内容以及 session 行为。

- `role`
  - 发给 gateway 的客户端角色名。
  - 通常是 `operator`。
- `message`
  - 默认要发送给模型的消息。
  - 只有在 `task_file` 为空时才会真正生效。
- `task_file`
  - 任务文件路径。
  - 非空时会优先读取对应 Markdown 里的 frontmatter `prompt`，并覆盖 `message`。
- `task_id`
  - task 文件 frontmatter 里的 `id`。
  - 由 harness 自动写入，不建议手工填写。
- `task_name`
  - task 文件 frontmatter 里的 `name`。
  - 由 harness 自动写入。
- `task_category`
  - task 文件 frontmatter 里的 `category`。
  - 由 harness 自动写入。
- `task_description`
  - task 文件 frontmatter 里的 `description`。
  - 由 harness 自动写入。
- `resolved_prompt`
  - 最终实际发给模型的 prompt。
  - 若 `task_file` 存在，这里会变成 task 里的 `prompt`。
- `session_prefix`
  - 会话 key 的前缀。
  - 用来把同一类测试的 session 区分开。
- `session_mode`
  - session 生成方式。
  - `per_worker` 表示每个 worker 一条。
  - `per_request` 表示每个请求一条。
  - `shared` 表示所有请求共用一条。
- `history_limit`
  - 每次 `chat.history` 最多拉回多少条消息。
- `wait_timeout_ms`
  - `agent.wait` 的超时时间，单位毫秒。
- `send_timeout_ms`
  - `chat.send` 的超时时间，单位毫秒。

### `load`

这一组控制负载形状。

- `concurrency`
  - 并发 worker 数量。
- `requests_per_worker`
  - 每个 worker 发送多少次请求。
- `worker_stagger_ms`
  - worker 启动错峰时间，单位毫秒。
  - 用于避免所有请求同时打上来。
- `request_pause_ms`
  - 同一 worker 内每次请求之间的暂停时间，单位毫秒。

### `collectors`

这一组控制采样器和性能数据采集。

- `docker_stats`
  - 采集容器 CPU / 内存等指标的开关和采样间隔。
- `pidstat`
  - 采集宿主机进程级 CPU / 内存 / IO 指标的开关和采样间隔。
- `perf_stat`
  - 采集 `perf stat` 指标的开关和采样间隔。
- `perf_record`
  - 是否开启 `perf record`。
  - 通常默认关闭，因为开销更大。
- `iostat`
  - 是否采集磁盘 IO 指标，以及采样间隔。

### `artifacts`

- `summary_only`
  - 产物策略。
  - `true` 时只保留 `summary.json`，适合只看汇总结果。
  - `false` 时保留完整运行产物。

## 最小示例

如果你只是想快速写一个可执行场景，最小结构大概是这样：

```json
{
  "name": "docker-single",
  "runtime": {
    "kind": "docker",
    "image": "openclaw:bench-local",
    "container_name_base": "openclaw-bench",
    "host": "127.0.0.1",
    "host_port": 19189,
    "container_port": 18789,
    "gateway_bind": "lan",
    "gateway_token": "openclaw-bench-token",
    "build_image_if_missing": true,
    "force_rebuild": false,
    "skip_channels": true,
    "startup_timeout_sec": 240
  },
  "client": {
    "role": "operator",
    "message": "/context list",
    "session_prefix": "bench-single",
    "session_mode": "per_worker",
    "history_limit": 20,
    "wait_timeout_ms": 15000,
    "send_timeout_ms": 15000
  },
  "load": {
    "concurrency": 1,
    "requests_per_worker": 3,
    "worker_stagger_ms": 0,
    "request_pause_ms": 0
  }
}
```

## 新建测试时怎么改

- 复用现有 task 时，只改 scenario 里的 `client.task_file` 和运行参数。
- 新建 task 时，先复制 `tasks/TASK_TEMPLATE.md`，再在 scenario 里引用它。
- 如果你不想用 task 文件，就只保留 `client.message`。
- 运行前可以先看 `scenario.resolved.json`，确认最终发给 gateway 的是哪个 prompt。
