# 实验计划与结果记录

## 1. 总体计划

| 实验类别 | Gateway | Gateway + vLLM |
| --- | --- | --- |
| 单实例多 session | ✅ 已完成 | ⬜ 未完成 |
| 单实例多 agent | ⬜ 未完成 | ⬜ 未完成 |
| 多实例多 session | ⬜ 未完成 | ⬜ 未完成 |

> 说明：目前仅完成了 `Gateway` 的“单实例多 session”实验。

## 2. 详细参数、实验与结论摘要

### 2.1 单实例多 session — Gateway Only

| 序号 | 机器 | 线程模式 | 任务/并发 | 模式 | stagger | req_pause | 是否完成 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 910c | single | 500 * 1w | worker | 0ms | 0ms | ✅ | 基线 gateway-only single-worker 已完成 |
| 2 | 910c | single | 500 * 1w | worker | 150ms | 0ms | ⬜ | 待跑 |
| 3 | 910c | single | 500 * 1w | worker | 300ms | 0ms | ⬜ | 待跑 |
| 4 | 910c | multi | 50 * 10w | worker | 0ms | 0ms | ⬜ | 待跑 |
| 5 | 910c | multi | 50 * 10w | request | 150ms | 0ms | ⬜ | 待跑 |
| 6 | 910c | multi | 50 * 10w | shared | 300ms | 0ms | ⬜ | 待跑 |
| 7 | hw cloud | single | 500 * 1w | worker | 0ms | 0ms | ⬜ | 计划比较稳定性 |
| 8 | hw cloud | single | 500 * 1w | worker | 150ms | 0ms | ⬜ | 对比本地表现 |
| 9 | local | single | 50 * 10w | request | 0ms | 0ms | ⬜ | 低资源场景验证 |

### 2.2 单实例多 session — Gateway + vLLM

| 序号 | 机器 | 线程模式 | 任务/并发 | 模式 | stagger | req_pause | 是否完成 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 910c | single | 500 * 1w | worker | 0ms | 0ms | ⬜ | 待跑 |
| 2 | 910c | single | 500 * 1w | worker | 150ms | 0ms | ⬜ | 待跑 |
| 3 | 910c | single | 500 * 1w | worker | 300ms | 0ms | ⬜ | 待跑 |
| 4 | 910c | multi | 50 * 10w | worker | 0ms | 0ms | ⬜ | 待跑 |
| 5 | 910c | multi | 50 * 10w | request | 150ms | 0ms | ⬜ | 待跑 |
| 6 | 910c | multi | 50 * 10w | shared | 300ms | 0ms | ⬜ | 待跑 |
| 7 | hw cloud | single | 500 * 1w | worker | 0ms | 0ms | ⬜ | 待跑 |
| 8 | hw cloud | single | 500 * 1w | worker | 150ms | 0ms | ⬜ | 待跑 |
| 9 | local | single | 50 * 10w | request | 0ms | 0ms | ⬜ | 待跑 |

### 2.3 多实例多 session — Gateway Only

| 序号 | 机器 | 线程模式 | 任务/并发 | 模式 | stagger | req_pause | 是否完成 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 910c | single | 500 * 1w | worker | 0ms | 0ms | ⬜ | 待跑 |
| 2 | 910c | single | 500 * 1w | worker | 150ms | 0ms | ⬜ | 待跑 |
| 3 | 910c | single | 500 * 1w | worker | 300ms | 0ms | ⬜ | 待跑 |
| 4 | 910c | multi | 50 * 10w | worker | 0ms | 0ms | ⬜ | 待跑 |
| 5 | 910c | multi | 50 * 10w | request | 150ms | 0ms | ⬜ | 待跑 |
| 6 | 910c | multi | 50 * 10w | shared | 300ms | 0ms | ⬜ | 待跑 |
| 7 | hw cloud | single | 500 * 1w | worker | 0ms | 0ms | ⬜ | 待跑 |
| 8 | hw cloud | single | 500 * 1w | worker | 150ms | 0ms | ⬜ | 待跑 |
| 9 | local | single | 50 * 10w | request | 0ms | 0ms | ⬜ | 待跑 |

### 2.4 多实例多 session — Gateway + vLLM

| 序号 | 机器 | 线程模式 | 任务/并发 | 模式 | stagger | req_pause | 是否完成 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 910c | single | 500 * 1w | worker | 0ms | 0ms | ⬜ | 待跑 |
| 2 | 910c | single | 500 * 1w | worker | 150ms | 0ms | ⬜ | 待跑 |
| 3 | 910c | single | 500 * 1w | worker | 300ms | 0ms | ⬜ | 待跑 |
| 4 | 910c | multi | 50 * 10w | worker | 0ms | 0ms | ⬜ | 待跑 |
| 5 | 910c | multi | 50 * 10w | request | 150ms | 0ms | ⬜ | 待跑 |
| 6 | 910c | multi | 50 * 10w | shared | 300ms | 0ms | ⬜ | 待跑 |
| 7 | hw cloud | single | 500 * 1w | worker | 0ms | 0ms | ⬜ | 待跑 |
| 8 | hw cloud | single | 500 * 1w | worker | 150ms | 0ms | ⬜ | 待跑 |
| 9 | local | single | 50 * 10w | request | 0ms | 0ms | ⬜ | 待跑 |
