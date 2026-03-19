---
id: task_01_openclaw_comprehension
name: OpenClaw Comprehension
category: comprehension
description: 参考 pinchbench 风格的多问答理解任务，但首版不要求写文件。
prompt: |
  你正在协助理解 OpenClaw benchmark harness。
  请回答下面 4 个问题：
  1. 这个 harness 的主要用途是什么？
  2. 本地 WSL 阶段推荐优先使用哪些观测方式？
  3. `host_direct` 和 `docker` 场景在运行形态上有什么核心区别？
  4. 为什么当前不建议把 WSL 上的 perf 结果当成正式结论？
  请按编号输出，每题 1-3 句。
---

# OpenClaw Comprehension

这是更接近真实问答理解的稳定任务，适合单线程延迟观测。
