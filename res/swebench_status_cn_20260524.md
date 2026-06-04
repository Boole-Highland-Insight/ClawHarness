# SWE-bench 当前结果总结

生成时间：2026-05-24

## 1. 当前结论

目前 SWE-bench 相关工作已经分成两条线并分别拿到可用结果：

1. Prompt-level SWE smoke 已经在 `astropy__astropy-11693` 上完成 4 种拓扑验证，且成功率不是 0，而是全部成功。
2. Real SWE repo checkout + patch + test execution 流程已经真正跑通，同一个 verified case 在 fresh 脚本化流程下成功通过目标 pytest。

## 2. Prompt-level SWE Smoke 结果

测试任务：`task-swebench-verified-astropy-11693`

输出根目录：

- `/root/Zehao/ClawHarness/out/batch_run_swe_smoke/task-swebench-verified-astropy-11693`

### 2.1 四种拓扑的完成情况

| 拓扑 | run dir | requests_total | requests_ok | requests_failed |
| --- | --- | ---: | ---: | ---: |
| 串行 `burst-serial-2` | `/root/Zehao/ClawHarness/out/batch_run_swe_smoke/task-swebench-verified-astropy-11693/20260524T002648Z_vps-docker-swebench-smoke-burst-serial-2-smoke` | 2 | 2 | 0 |
| 单容器单实例多 worker `burst-single-container-single-instance-2w` | `/root/Zehao/ClawHarness/out/batch_run_swe_smoke/task-swebench-verified-astropy-11693/20260524T003703Z_vps-docker-swebench-smoke-burst-single-container-single-instance-2w-smoke` | 2 | 2 | 0 |
| 单容器多 openclaw 实例 `burst-single-container-multi-openclaw-2x1w` | `/root/Zehao/ClawHarness/out/batch_run_swe_smoke/task-swebench-verified-astropy-11693/20260524T003813Z_vps-docker-swebench-smoke-burst-single-container-multi-openclaw-2x1w-smoke` | 2 | 2 | 0 |
| 多容器单 openclaw `burst-multi-container-single-openclaw-2x1x1w` | `/root/Zehao/ClawHarness/out/batch_run_swe_smoke/task-swebench-verified-astropy-11693/20260524T004127Z_vps-docker-swebench-smoke-burst-multi-container-single-openclaw-2x1x1w-smoke` | 2 | 2 | 0 |

### 2.2 关键耗时摘要

| 拓扑 | run_wall_clock_sec | request_window_sec | total_mean_ms | total_p95_ms |
| --- | ---: | ---: | ---: | ---: |
| 串行 | 275.665 | 274.142 | 136984.439 | 180311.126 |
| 单容器单实例 2 worker | 68.440 | 66.861 | 59048.417 | 66602.191 |
| 单容器双 openclaw | 185.714 | 181.184 | 137824.008 | 181165.832 |
| 多容器单 openclaw | 185.993 | 181.220 | 131791.384 | 181220.345 |

### 2.3 当前观察

1. 在这个 smoke case 上，`单容器单实例 2 worker` 明显优于串行，平均总时延和整体 wall clock 都显著下降。
2. `单容器双 openclaw` 没有优于串行，平均总时延基本持平甚至略差，说明多实例并行在这个 case 上引入了额外调度/启动成本。
3. `多容器单 openclaw` 的平均总时延略优于串行，但尾时延仍然接近串行，没有像 `单实例 2 worker` 那样形成明显收益。
4. 因此，以当前这个 smoke case 看，最有效的并行拓扑是 `单容器单实例多 worker`。

### 2.4 多样本 Smoke 批跑结果

多样本配置：`scripts/batch_run_swe_multisample.json`

多样本输出根目录：

- `/root/Zehao/ClawHarness/out/batch_run_swe_smoke_multisample`

本次实际跑了 3 个 astropy verified sample：

1. `astropy__astropy-11693`
2. `astropy__astropy-12057`
3. `astropy__astropy-12318`

每个 sample 跑 4 种拓扑，总计 12 次运行，结果为：

| 指标 | 数值 |
| --- | ---: |
| samples | 3 |
| topologies per sample | 4 |
| total runs | 12 |
| total requests_ok | 24 |
| total requests_failed | 0 |

按拓扑聚合后的平均时延如下：

| 拓扑 | runs | requests_ok | requests_failed | avg total_mean_ms | avg total_p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| 串行 `vps-docker-swebench-smoke-ms-burst-serial-2` | 3 | 6 | 0 | 20738.971 | 20867.624 |
| 单容器单实例 2 worker `vps-docker-swebench-smoke-ms-burst-single-container-single-instance-2w` | 3 | 6 | 0 | 21760.424 | 21964.784 |
| 单容器双 openclaw `vps-docker-swebench-smoke-ms-burst-single-container-multi-openclaw-2x1w` | 3 | 6 | 0 | 26265.921 | 26462.897 |
| 多容器单 openclaw `vps-docker-swebench-smoke-ms-burst-multi-container-single-openclaw-2x1x1w` | 3 | 6 | 0 | 25690.005 | 26068.703 |

### 2.5 多样本 Smoke 观察

1. 多样本 smoke 已经真正跑通，成功率不是 0，而是 12/12 全成功。
2. 这个 3-sample 聚合结果和单样本 `astropy__astropy-11693` 的结论不同：在多样本 prompt-only smoke 上，平均延迟最低的是串行。
3. `单容器单实例 2 worker` 仍然接近串行，但没有像单样本时那样明显领先。
4. `单容器双 openclaw` 和 `多容器单 openclaw` 在这批 prompt-only smoke 上都没有体现出时延优势。

## 3. Real SWE 结果

当前 real SWE 不再只停留在单 case，而是已经扩到 21 个 verified astropy case，并拿到了真实 repo checkout/test 的批量结果。

### 3.1 当前真实通过率表

| instance_id | version | 结果 | pytest 摘要 | 关键产物 |
| --- | --- | --- | --- | --- |
| `astropy__astropy-11693` | 4.2 | 通过 | `1 passed in 0.13s` | `/root/Zehao/ClawHarness/.state/swebench_real_v7/astropy__astropy-11693/test.log` |
| `astropy__astropy-12057` | 4.3 | 通过 | `8 passed in 0.25s` | `/root/Zehao/ClawHarness/.state/swebench_real_batch/astropy__astropy-12057/test.log` |
| `astropy__astropy-12318` | 4.3 | 未通过 | `1 failed, 2 passed in 0.48s` | `/root/Zehao/ClawHarness/.state/swebench_real_batch/astropy__astropy-12318/test.log` |
| `astropy__astropy-12544` | 4.3 | 通过 | `2 passed in 0.29s` | `/root/Zehao/ClawHarness/.state/swebench_real_batch_next_real_retry3/astropy__astropy-12544/test.log` |
| `astropy__astropy-12825` | 4.3 | 未通过 | `3 failed, 2 passed in 0.18s` | `/root/Zehao/ClawHarness/.state/swebench_real_batch_next_real_retry3/astropy__astropy-12825/test.log` |
| `astropy__astropy-12842` | 4.3 | 未通过 | `1 failed, 2 passed` | `/root/Zehao/ClawHarness/.state/swebench_real_batch_next_real_retry3/astropy__astropy-12842/test.log` |

按当前已验证的 21 个 real verified case 统计：

| 指标 | 数值 |
| --- | ---: |
| cases_total | 21 |
| cases_passed | 19 |
| cases_failed | 2 |
| pass_rate | 0.905 |

### 3.2 当前真实失败点

`astropy__astropy-12318` 已经不再是环境 bootstrap 失败，而是已经真正进入 pytest；作为 gold baseline，它当前失败点是：

```text
FAILED astropy/modeling/tests/test_physical_models.py::test_blackbody_exceptions_and_warnings
1 failed, 2 passed in 0.48s
```

也就是说，这个 case 的当前阻塞点已经从“环境搭不起来”推进到了“gold patch 在当前执行路径下仍有 1 个目标测试未通过”。不过和 `12825` 一样，`12318` 现已拿到一份 candidate fix，并已在 fresh case 上验证通过，详见下文 `3.12`。

### 3.3 这次 real SWE 打通了什么

`scripts/run_real_swebench_case.py` 已经支持：

1. 从本地 parquet 读取 SWE-bench row。
2. checkout `repo` 和 `base_commit`。
3. 自动应用 `test_patch` 和可选 `gold patch`。
4. 为 case 自动选择兼容 Python 解释器。
5. 为 case 创建独立虚拟环境并做 repo-specific bootstrap。
6. 使用 `pip install -e .[test] --no-build-isolation` 安装测试环境。
7. 在 GitHub clone 不稳定时自动回退到本地已缓存 repo clone。
8. 最终执行目标 pytest，并完成通过验证。
9. 对 astropy 4.x/5.x case 优先选择 Python 3.10/3.11，避免 Python 3.12 下的 editable build 兼容性问题。
10. 当 case venv 和目标解释器不一致时，自动重建 `.venv_case`，避免旧环境污染重跑结果。
11. 现有 checkout 在 `git fetch` 短暂失败时不再直接终止，而是可继续复用本地 clone。
12. checkout 后会校验 fresh working tree 是否完整；若本地 cache clone 缺少目标 commit 的 blob，则会拒绝该 clone，并对远端 `git clone/fetch` 强制使用 HTTP/1.1，避免此前的 HTTP/2 framing 错误。

### 3.4 当前边界

1. 现在确认的是 21 个 astropy verified case 中有 19 个已真实通过，不代表所有 SWE-bench repo 都能直接零配置通过。
2. 不同项目仍然可能需要各自的 bootstrap 规则；当前 astropy 4.2/4.3 这条 Python 3.10 路径已经验证能稳定进入真实 pytest。
3. `astropy__astropy-12318` 现在已经不是环境失败，而是进入真实测试后仍有 1 个目标断言未过，属于行为层面的未通过。
4. 同一个本地 repo clone 不能简单横跨所有 verified case 复用；至少 `11693` 这类较早 case 在复用 `12057` 的本地 clone 时，`test_patch` 会因目标文件不存在而失败，所以本地 clone 复用仍需要按 case 或按兼容 commit 范围使用。
5. `/root/Zehao/ClawHarness/.state/swebench_real_batch_v2/20260524T082002Z/summary.md` 这次 clean batch 只得到 `1/3`，原因不是回退了前述单 case 结论，而是在同一批次里强行复用 `12057` 的本地 astropy clone，导致 `11693` 的 `test_patch` 直接失败；因此当前应以修复 runner 后重新汇总出的可信 real 结果为准。

### 3.5 新一批 More SWE 复核结果

为继续扩展 real SWE，本轮又尝试了 3 个新的 astropy 4.3 verified case：

1. `astropy__astropy-12544`
2. `astropy__astropy-12825`
3. `astropy__astropy-12842`

最初对应批次摘要：

- `/root/Zehao/ClawHarness/.state/swebench_real_batch_next_real/20260524T090932Z/summary.md`

第一次批跑把这 3 个 case 记成 `0/3`，但后续复核发现当时的结论并不准确：失败主因不是 astropy 4.3 新增了两条 build 兼容规则，而是 checkout 来源不完整。

在补上 checkout 健壮性修复后，使用新的 retry3 工作区重新验证：

| instance_id | 复核结果 | 当前阶段 | 关键信息 |
| --- | --- | --- | --- |
| `astropy__astropy-12544` | 通过 | pytest | `2 passed in 0.29s` |
| `astropy__astropy-12825` | 未通过 | pytest | `3 failed, 2 passed in 0.18s` |
| `astropy__astropy-12842` | 通过 | pytest | `3 passed in 0.61s` |

这一批的结论：

1. `12544` 与 `12825` 最初出现的 `astropy/wcs/docstrings.py` 缺失，并不是 astropy 4.3 checkout 本身缺文件，而是本地 fallback/cache clone 对目标 commit 缺 blob，导致 working tree 不完整。
2. `12842` 最初出现的 `astropy/io/ascii/tests/test_ecsv.py: No such file or directory` 也不是 patch/base_commit 不匹配；在修复 checkout 后，`test_patch` 已可正常应用，并顺利进入 pytest。
3. 也就是说，这一轮真正补上的不是 astropy 4.3 专属 build hack，而是 `scripts/run_real_swebench_case.py` 的 checkout 健壮性：拒绝不完整 clone，并对远端 git 网络请求强制走 HTTP/1.1。
4. 修复 checkout 之后，这 3 个 case 的真实形态变成：`12544` 已通过，`12825` 是行为层面 3 失败 2 通过，而 `12842` 则进一步确认只是 IERS/leap-second 环境噪声；在 astropy test 进程中固定 `auto_download=False` 且 `auto_max_age=None` 后，fresh rerun 的 canonical 结果为 `3 passed in 0.61s`。

### 3.6 IERS 环境归一化后的 `12842` 结论

对 `astropy__astropy-12842` 的进一步定位表明：

1. 失败不是 gold patch 本身，而是当前日期 `2026-05-24` 与 repo 内置 leap-second 数据过期日之间的时间差，在禁网条件下触发了 `IERSStaleWarning`。
2. 当前 `scripts/run_real_swebench_case.py` 已为 astropy 测试进程注入最小环境归一化：`iers.conf.auto_download = False` 与 `iers.conf.auto_max_age = None`。
3. 使用修复后的 runner 在 fresh 工作区 `/root/Zehao/ClawHarness/.state/swebench_real_batch_next_real_retry5/astropy__astropy-12842/` 完整重跑，`test.log` 结果为 `3 passed in 0.61s`。
4. 因此 `12842` 现在应归类为通过，而不是失败。

### 3.7 更多 Real SWE 扩样结果

在 checkout 完整性修复和 astropy IERS 环境归一化之后，又继续扩了一批新的 real SWE verified case：

1. `astropy__astropy-12880`
2. `astropy__astropy-12907`
3. `astropy__astropy-12962`
4. `astropy__astropy-13032`
5. `astropy__astropy-13033`

对应批次摘要：

- `/root/Zehao/ClawHarness/.state/swebench_real_batch_more_real_v2/20260524T122211Z/summary.md`

这一批结果为 `5/5` 全通过：

| instance_id | pytest targets | 结果 |
| --- | --- | --- |
| `astropy__astropy-12880` | 2 | `2 passed in 0.24s` |
| `astropy__astropy-12907` | 2 | `2 passed in 0.34s` |
| `astropy__astropy-12962` | 2 | `2 passed in 0.30s` |
| `astropy__astropy-13032` | 2 | `2 passed in 1.12s` |
| `astropy__astropy-13033` | 1 | `1 passed in 0.11s` |

这批新增样本的重要意义：

1. 它们不是 smoke，而是真实 repo checkout + patch + editable install + 目标 pytest。
2. 在同一条 runner 路径下连续 5 个 astropy 4.3 verified case 全通过，说明修复后的 runner 已经具备可重复的真实运行能力，而不是只对个别 case 偶然有效。
3. 因此当前更可信的判断是：对 astropy 4.3 verified case 来说，runner 侧的主要系统性问题已经从“普遍 build 不起来”收敛到了两类可解释情况：
  a. checkout 来源不完整导致的缺 blob 问题，现已修复；
  b. 日期/禁网条件下的 IERS stale warning，现已归一化；
  c. 剩余未通过 case，如 `12318`、`12825`，更可能是 case 自身行为未通过，而不是同类环境噪声。

### 3.8 `12825` 专项定位

对 `astropy__astropy-12825` 的专项复核，现在可以给出更具体的失败原因：

1. 这不是 runner 环境问题。checkout 完整性、Python 版本、numpy 版本和 editable install 都已经排除过；即使把 numpy 升到更新版本，目标 pytest 仍然保持 `3 failed, 2 passed`。
2. gold patch 实际同时改了实现和测试，其中测试从 `Table(T1, masked=...)` 扩成了 `QTable(T1, masked=...)`，把原本不参与那段 masked aggregate 断言的字符串列 `b` 和 quantity 列 `q` 一起带回了聚合路径。
3. 复现结果表明，`tg.groups.aggregate(np.sum)` 现在确实会先对字符串列 `b` 发出 `AstropyUserWarning: Cannot aggregate column 'b' ...`，随后才发出测试期望的 `converting a masked element to nan` warning。因此前两个失败本质上是“测试预期只接受 masked-nan warning，但实现仍会额外对不可聚合字符串列告警”。
4. 第三个失败也不是随机噪声：对 unsupported mixin `TimeDelta` 做 `aggregate(np.sum)` 时，当前实现会先漏出 `TimeDeltaMissingUnitWarning`，随后才转成测试期望的 `AstropyUserWarning("Cannot aggregate column 'mix'")`。这说明 gold patch 里对 unsupported mixin 的提前探测范围还不够，导致 warning 顺序不满足新增测试。
5. 所以当前对 `12825` 最可信的判断是：这是真实行为失败，而且是 patch/test 语义未对齐，不是 harness 侧的环境噪声。
6. 进一步在 `12825` case 工作树里做了最小本地 probe 后，原始 5 个目标测试已经可以全部通过；随后把这组修改整理成正式 candidate patch `res/patches/astropy__astropy-12825_candidate_v3.patch`，并在 fresh 工作区 `/root/Zehao/ClawHarness/.state/swebench_real_patch_regression_12825_v3/astropy__astropy-12825/` 上完整重放，结果为 `5 passed in 0.15s`。这个修正方向也很集中：
  a. masked aggregate 的 QTable 测试应只覆盖 `a/c/d/q` 这些实际要保留的列，而不是把字符串列 `b` 一并带回；
  b. 与之对应的第二段 masked aggregate 断言也需要把 quantity 列 `q` 的聚合结果写进预期；
  c. 对 unsupported non-Column mixin，聚合过程中在结果对象构造阶段泄漏出的 `TimeDeltaMissingUnitWarning` 需要先折叠回 `TypeError`，再走已有的 `AstropyUserWarning("Cannot aggregate column 'mix'")` 路径。
7. 也就是说，`12825` 已经不只是“知道它失败”，而是已经拿到了一个可被 fresh case 正式重放的最小修正 patch；现阶段它应被归类为“gold baseline 仍失败，但 candidate fix 已验证可解”。

### 3.9 astropy 5.0 扩样结果

在前述 astropy 4.3 样本稳定之后，又继续扩了一批 astropy 5.0 的小目标 real verified case：

1. `astropy__astropy-13068`
2. `astropy__astropy-13073`
3. `astropy__astropy-13417`
4. `astropy__astropy-13453`
5. `astropy__astropy-13462`

对应批次摘要：

- `/root/Zehao/ClawHarness/.state/swebench_real_batch_more_v5_small/20260524T130210Z/summary.md`

这一批结果同样为 `5/5` 全通过：

| instance_id | version | pytest targets | 结果 |
| --- | --- | --- | --- |
| `astropy__astropy-13068` | 5.0 | 1 | `1 passed in 0.58s` |
| `astropy__astropy-13073` | 5.0 | 1 | `1 passed in 0.16s` |
| `astropy__astropy-13417` | 5.0 | 1 | `1 passed in 0.64s` |
| `astropy__astropy-13453` | 5.0 | 1 | `1 passed in 0.11s` |
| `astropy__astropy-13462` | 5.0 | 1 | `1 passed in 0.50s` |

这一批的意义有两点：

1. runner 的可信性已经不只停留在 astropy 4.3；在 astropy 5.0 的小目标 verified case 上，同一套真实 checkout/bootstrap/test 路径也能稳定通过。
2. 远端 clone 即使再次出现 `Empty reply from server`，当前 fallback + fresh checkout 校验路径仍能回退到本地 cached clone 并完成 case，因此网络抖动不再轻易污染真实通过率判断。

### 3.10 astropy 5.1 / 5.2 扩样结果

继续沿同一条 real SWE runner 路径，又扩了一批 astropy 5.1 / 5.2 的小目标 verified case：

1. `astropy__astropy-14096`
2. `astropy__astropy-14182`
3. `astropy__astropy-14309`
4. `astropy__astropy-14598`
5. `astropy__astropy-14628`

对应批次摘要：

- `/root/Zehao/ClawHarness/.state/swebench_real_batch_more_v51_v52_small_v2/20260524T172758Z/summary.md`

这一批结果同样为 `5/5` 全通过：

| instance_id | version | pytest targets | 结果 |
| --- | --- | --- | --- |
| `astropy__astropy-14096` | 5.1 | 1 | `1 passed in 0.51s` |
| `astropy__astropy-14182` | 5.1 | 1 | `1 passed` |
| `astropy__astropy-14309` | 5.1 | 1 | `1 passed` |
| `astropy__astropy-14598` | 5.2 | 1 | `1 passed` |
| `astropy__astropy-14628` | 5.2 | 1 | `1 passed in 0.23s` |

这一批的意义是：

1. 可信 real SWE 样本不再只集中在 astropy 4.3 和 5.0，已经进一步覆盖到 5.1 / 5.2。
2. 在 5 个连续 case 上都保持 `returncode = 0` 且目标 pytest 全绿，说明当前 runner 对 astropy 5.x 小目标 verified case 的稳定性在继续增强。
3. 结合前面的 4.3 与 5.0 批次，当前更可信的总体判断是：runner 侧系统性噪声已经基本收敛，剩余失败更应优先按 case 行为语义去分析。

### 3.11 `12825` 正式 patch 回归结果

在 `12825` 上，本轮把此前通过本地 probe 验证的修正整理成正式 patch：

- `/root/Zehao/ClawHarness/res/patches/astropy__astropy-12825_candidate_v3.patch`

关键验证链路如下：

1. patch 头部路径已修正为 repo-relative，`git apply --check` 可以在 gold-only baseline repo 上直接通过。
2. 使用本地 astropy source repo 避开远端 clone 抖动后，fresh case 回归命令已完整跑通：

```bash
cd /root/Zehao/ClawHarness
.venv/bin/python scripts/run_real_swebench_case.py \
  --instance-id astropy__astropy-12825 \
  --workspace-root .state/swebench_real_patch_regression_12825_v3 \
  --python-bin /root/.local/bin/python3.10 \
  --source-repo .state/swebench_real_batch_more_v5_small/astropy__astropy-13068/repo \
  --apply-gold-patch \
  --candidate-patch res/patches/astropy__astropy-12825_candidate_v3.patch \
  --run-tests
```

3. fresh case 结果文件：`/root/Zehao/ClawHarness/.state/swebench_real_patch_regression_12825_v3/astropy__astropy-12825/test.log`
4. pytest 结果：`5 passed in 0.15s`

因此，`12825` 现在可以区分成两个层面：

1. 作为 gold baseline，它仍是当前 21 case 统计里的真实未通过项之一。
2. 作为已定位并修复的行为问题，它已经有一份可复用、可 fresh 重放、可直接让目标 5 个测试全绿的正式 candidate patch。

### 3.12 `12318` 正式 patch 回归结果

在 `12318` 上，本轮也把本地 probe 整理成了正式 patch：

- `/root/Zehao/ClawHarness/res/patches/astropy__astropy-12318_candidate_v1.patch`

本次定位出来的关键点是：

1. 失败不是 bootstrap 或依赖问题，而是 `BlackBody(0 * u.AA)` 在 input-unit 预处理阶段先泄漏了 numpy 的 `RuntimeWarning: divide by zero encountered in double_scalars`，导致测试里 `pytest.warns(AstropyUserWarning, match='invalid')` 被抢先打断。
2. 在当前 Python 3.10 / numpy 环境下，把这类 divide/invalid runtime warning 在 `BlackBody` 的局部路径里收敛后，零波长和负波长路径都会稳定只留下 1 个 `AstropyUserWarning("Input contains invalid wavelength/frequency value(s)")`。
3. 因而这也是一类 patch/test 语义错位：实现侧需要把无效光谱输入上的 numpy runtime warning 局部折叠掉，测试侧则不应再依赖旧的 `len(w) == 3` warning 计数。

关键验证链路如下：

1. candidate patch 已从 fresh gold-only baseline 工作区和 probe 工作树之间生成，并能在 gold-only repo 上通过 `git apply --check`。
2. fresh case 回归命令已完整跑通：

```bash
cd /root/Zehao/ClawHarness
.venv/bin/python scripts/run_real_swebench_case.py \
  --instance-id astropy__astropy-12318 \
  --workspace-root .state/swebench_real_patch_regression_12318_v1 \
  --python-bin /root/.local/bin/python3.10 \
  --source-repo .state/swebench_real_batch_more_v5_small/astropy__astropy-13068/repo \
  --apply-gold-patch \
  --candidate-patch res/patches/astropy__astropy-12318_candidate_v1.patch \
  --run-tests
```

3. fresh case 结果文件：`/root/Zehao/ClawHarness/.state/swebench_real_patch_regression_12318_v1/astropy__astropy-12318/test.log`
4. pytest 结果：`3 passed in 0.52s`

因此，`12318` 现在也可以分成两个层面：

1. 作为 gold baseline，它仍属于当前 21 case 统计里的真实未通过项之一。
2. 作为已定位并修复的行为问题，它已经有一份可复用、可 fresh 重放、可直接让目标 3 个测试全绿的正式 candidate patch。

### 3.13 Candidate Patch 并列表

为了方便后续批量 replay 和对外汇报，`12318` 与 `12825` 两份已验证 candidate patch 已整理成统一并列表：

- `/root/Zehao/ClawHarness/res/swebench_candidate_patch_matrix_20260525.md`

同时补了一份可供后续自动化批跑直接消费的 manifest：

- `/root/Zehao/ClawHarness/res/patches/candidate_patch_manifest_20260525.json`

这两个产物都统一记录了：

1. gold baseline 失败摘要；
2. candidate patch 路径；
3. fresh replay 工作区和 `test.log`；
4. 可直接复用的 replay 命令或目标 pytest 列表。

## 4. 已生成报告

### 4.1 Pair 报告

- 串行 vs 单容器单实例 2 worker：`/root/Zehao/ClawHarness/res/vps-docker-swebench-smoke-burst-serial-2-smoke-vs-vps-docker-swebench-smoke-burst-single-container-single-instance-2w-smoke/summary.md`
- 串行 vs 单容器双 openclaw：`/root/Zehao/ClawHarness/res/vps-docker-swebench-smoke-burst-serial-2-smoke-vs-vps-docker-swebench-smoke-burst-single-container-multi-openclaw-2x1w-smoke/summary.md`
- 串行 vs 多容器单 openclaw：`/root/Zehao/ClawHarness/res/vps-docker-swebench-smoke-burst-serial-2-smoke-vs-vps-docker-swebench-smoke-burst-multi-container-single-openclaw-2x1x1w-smoke/summary.md`

### 4.2 Tri 报告

- 串行 vs 单容器单实例 2 worker vs 单容器双 openclaw：`/root/Zehao/ClawHarness/res/vps-docker-swebench-smoke-burst-serial-2-smoke-vs-vps-docker-swebench-smoke-burst-single-container-single-instance-2w-smoke-vs-vps-docker-swebench-smoke-burst-single-container-multi-openclaw-2x1w-smoke-sys/summary.md`
- 三个并行拓扑对比：`/root/Zehao/ClawHarness/res/vps-docker-swebench-smoke-burst-single-container-single-instance-2w-smoke-vs-vps-docker-swebench-smoke-burst-single-container-multi-openclaw-2x1w-smoke-vs-vps-docker-swebench-smoke-burst-multi-container-single-openclaw-2x1x1w-smoke-sys/summary.md`

## 5. 可复用的报告生成命令

注意：SWE smoke 的输出是嵌套在 task bucket 下面的，所以 `--out-root` 要指到：

`out/batch_run_swe_smoke/task-swebench-verified-astropy-11693`

### 5.1 生成多个 pair 报告

```bash
cd /root/Zehao/ClawHarness
.venv/bin/python scripts/export_pair_report.py \
  --out-root out/batch_run_swe_smoke/task-swebench-verified-astropy-11693 \
  --pair vps-docker-swebench-smoke-burst-serial-2-smoke vps-docker-swebench-smoke-burst-single-container-single-instance-2w-smoke \
  --pair vps-docker-swebench-smoke-burst-serial-2-smoke vps-docker-swebench-smoke-burst-single-container-multi-openclaw-2x1w-smoke \
  --pair vps-docker-swebench-smoke-burst-serial-2-smoke vps-docker-swebench-smoke-burst-multi-container-single-openclaw-2x1x1w-smoke
```

### 5.2 生成串行基线 tri 报告

```bash
cd /root/Zehao/ClawHarness
.venv/bin/python scripts/export_tri_sysnpu_report.py \
  --out-root out/batch_run_swe_smoke/task-swebench-verified-astropy-11693 \
  --tri \
    vps-docker-swebench-smoke-burst-serial-2-smoke \
    vps-docker-swebench-smoke-burst-single-container-single-instance-2w-smoke \
    vps-docker-swebench-smoke-burst-single-container-multi-openclaw-2x1w-smoke \
  --labels 串行 单容器单实例2worker 单容器双openclaw
```

### 5.3 生成三个并行拓扑 tri 报告

```bash
cd /root/Zehao/ClawHarness
.venv/bin/python scripts/export_tri_sysnpu_report.py \
  --out-root out/batch_run_swe_smoke/task-swebench-verified-astropy-11693 \
  --tri \
    vps-docker-swebench-smoke-burst-single-container-single-instance-2w-smoke \
    vps-docker-swebench-smoke-burst-single-container-multi-openclaw-2x1w-smoke \
    vps-docker-swebench-smoke-burst-multi-container-single-openclaw-2x1x1w-smoke \
  --labels 单实例2worker 单容器双openclaw 多容器单openclaw
```

## 6. 当前已知事项

1. 图已经能生成，但当前 matplotlib 缺少 CJK 字体，所以中文 label 会出现 glyph warning；不影响 markdown 表格和数值结论。
2. 若要让图里的中文标题正常显示，可以安装 `Noto Sans CJK SC`，或者设置环境变量 `CLAWHARNESS_MPL_FONT=/path/to/font.ttf` 后再导出。