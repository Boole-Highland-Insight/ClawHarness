# SWE-bench 对外摘要

生成时间：2026-05-25

## 1. 一页结论

本轮 SWE-bench 工作分成两条线：

1. `Prompt-level smoke / 结构对比`：用于比较不同部署结构在 SWE 任务上的时延与成功率。
2. `Real SWE repo-based execution`：用于验证真实 repo checkout + patch + pytest 流程是否跑通，并定位 gold baseline 的真实行为失败。

当前最关键的对外结论是：

1. 已完成 `4` 个 SWE smoke 任务的结构对比工作：其中 `1` 个是单任务四拓扑对比，`3` 个是多样本 smoke 扩展；若按唯一任务计数，则是 `3` 个唯一 astropy SWE 任务（`11693`、`12057`、`12318`）。
2. 已完成 `21` 个 real SWE verified astropy case 的真实 repo/test 验证，gold-baseline 通过率为 `19/21 = 90.5%`。
3. 对剩余 `2` 个 gold-baseline 行为失败项，已经各自整理出一份 candidate patch，并都在 fresh replay 中验证通过：
   - `astropy__astropy-12318`: `3 passed in 0.52s`
   - `astropy__astropy-12825`: `5 passed in 0.15s`

## 2. 跑了多少个 SWE 任务

按用途拆分如下：

| 类别 | 任务/Case 数 | 说明 |
| --- | ---: | --- |
| 单任务 smoke 结构对比 | 1 | `astropy__astropy-11693`，在 4 种结构上各跑 1 轮 |
| 多样本 smoke 结构对比 | 3 | `11693`、`12057`、`12318`，每个任务都跑 4 种结构 |
| smoke 总运行次数 | 16 | `1 x 4` + `3 x 4` |
| real SWE verified case | 21 | 真实 repo checkout + patch + pytest |
| candidate patch 已 formalize 的失败 case | 2 | `12318`、`12825` |

如果按“唯一 SWE 任务数”来讲：

1. 结构对比阶段覆盖了 `3` 个唯一 astropy SWE 任务。
2. 真实 repo/test 阶段覆盖了 `21` 个 verified case。

## 3. 对比了哪几种结构

本轮结构对比统一使用了 `4` 种部署/并发结构：

| 结构 | 配置键 | 含义 |
| --- | --- | --- |
| 串行 | `burst-serial-2` | 单容器、单 openclaw、单 worker |
| 单容器单实例多 worker | `burst-single-container-single-instance-2w` | 单容器、单 openclaw、2 worker 并发 |
| 单容器多 openclaw | `burst-single-container-multi-openclaw-2x1w` | 单容器、2 个 openclaw 实例、每个 1 worker |
| 多容器单 openclaw | `burst-multi-container-single-openclaw-2x1x1w` | 2 个容器、每容器 1 个 openclaw、每个 1 worker |

对外可以把它们概括成：

1. `串行基线`
2. `单容器内 worker 并发`
3. `单容器内多 openclaw 实例`
4. `多容器横向扩展`

## 4. 是 burst 模式还是之前的模式

这轮结构对比使用的是 `burst` 模式，不是之前那种普通串行/手工逐请求模式。

依据如下：

1. smoke 配置模板直接来自 `scenarios/vllm/vps_docker_burst_task_01_100_session10.json`。
2. 两份批跑配置里都显式设置了 `load.dispatch_mode = "burst"`。
3. 所有结构键名也都带 `burst-*` 前缀。

因此，对外表述应为：

`本轮结构对比是在 burst dispatch 模式下完成的。`

## 5. 请求数是不是固定的

结论要分“对外结果口径”和“底层配置口径”两层说：

1. 对外结果口径：结构对比阶段每轮都按 `2` 个完成请求来比较，单任务 smoke 四种结构的最终统计都是 `requests_ok = 2`、`requests_failed = 0`。
2. 多样本 smoke 也是同样口径：`3` 个样本 x `4` 种结构，共 `12` 次运行，累计 `24` 个成功请求、`0` 个失败请求。
3. 底层配置口径：大多数结构显式写的是 `total_requests = 2`；多容器单 openclaw 这一档虽然配置字段写法不同，但最终对外统计口径仍然落在每轮 `2` 个完成请求上。

因此，对外更稳妥的表述是：

`本轮结构对比采用固定的小请求规模进行横向比较，按最终统计口径看，每种结构每轮都对齐为 2 个完成请求。`

## 6. 对外建议表述

可以直接使用下面这段：

> 本轮 SWE-bench 评估分为两部分：一部分是在 burst 模式下对 4 种部署结构做 prompt-level smoke 对比，覆盖 3 个唯一 astropy SWE 任务、共 16 次运行；另一部分是对 21 个 real SWE verified astropy case 做真实 repo checkout + patch + pytest 验证，当前 gold-baseline 通过率为 19/21。对剩余 2 个真实行为失败 case（12318、12825），我们都已经整理出 candidate patch，并分别在 fresh replay 中验证通过。

## 7. 相关产物

- 详细候选 patch 并列表：`/root/Zehao/ClawHarness/res/swebench_candidate_patch_matrix_20260525.md`
- 批量 replay manifest：`/root/Zehao/ClawHarness/res/patches/candidate_patch_manifest_20260525.json`
- 中文总总结：`/root/Zehao/ClawHarness/res/swebench_status_cn_20260524.md`